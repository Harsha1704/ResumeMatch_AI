import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  ShieldCheck,
  Sun,
  Moon,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Video,
  VideoOff,
  UserCheck,
  UserX,
  Maximize2,
} from 'lucide-react';

export type WebcamStatus =
  | 'disabled'
  | 'requesting'
  | 'active'
  | 'denied'
  | 'unavailable'
  | 'disconnected'
  | 'unsupported';

export interface VisualPresenceMetrics {
  lightingQuality: 'good' | 'low' | 'bright' | 'unknown';
  luminanceScore: number;
  faceDetected: boolean | null; // null if native FaceDetector not available
  isCentered: boolean | null;
  feedbackMessage: string;
}

interface CandidateWebcamPreviewProps {
  isInterviewCompleted?: boolean;
  onStatusChange?: (status: WebcamStatus) => void;
}

export const CandidateWebcamPreview: React.FC<CandidateWebcamPreviewProps> = ({
  isInterviewCompleted = false,
  onStatusChange,
}) => {
  const [status, setStatus] = useState<WebcamStatus>('disabled');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [availableCameras, setAvailableCameras] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [metrics, setMetrics] = useState<VisualPresenceMetrics>({
    lightingQuality: 'unknown',
    luminanceScore: 0,
    faceDetected: null,
    isCentered: null,
    feedbackMessage: 'Camera disabled',
  });

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analysisTimerRef = useRef<any>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const updateStatus = useCallback((newStatus: WebcamStatus) => {
    setStatus(newStatus);
    if (onStatusChange) {
      onStatusChange(newStatus);
    }
  }, [onStatusChange]);

  // Clean up all media stream tracks
  const stopTracks = useCallback(() => {
    if (analysisTimerRef.current) {
      clearInterval(analysisTimerRef.current);
      analysisTimerRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (e) {
          // Ignored
        }
      });
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Stop video stream immediately when interview completes
  useEffect(() => {
    if (isInterviewCompleted && status === 'active') {
      stopTracks();
      updateStatus('disabled');
    }
  }, [isInterviewCompleted, status, stopTracks, updateStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTracks();
    };
  }, [stopTracks]);

  // Enumerate cameras
  const enumerateCameras = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      return;
    }
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter((d) => d.kind === 'videoinput');
      setAvailableCameras(videoDevices);
      if (videoDevices.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(videoDevices[0].deviceId);
      }
    } catch (e) {
      // Ignored
    }
  }, [selectedDeviceId]);

  // Handle device change (e.g. webcam plugged/unplugged)
  useEffect(() => {
    if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      const handleDeviceChange = () => {
        enumerateCameras();
        // If current camera was unplugged
        if (streamRef.current) {
          const videoTrack = streamRef.current.getVideoTracks()[0];
          if (!videoTrack || videoTrack.readyState === 'ended') {
            stopTracks();
            updateStatus('disconnected');
            setErrorMessage('Camera was disconnected.');
          }
        }
      };

      navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);
      return () => {
        navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange);
      };
    }
  }, [enumerateCameras, stopTracks, updateStatus]);

  // Local Visual Analysis (Luminance + Optional Native Face Detection)
  const runVisualChecks = useCallback(async () => {
    const video = videoRef.current;
    if (!video || video.readyState < 2 || !video.videoWidth) return;

    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return;

    const w = 160;
    const h = 120;
    canvas.width = w;
    canvas.height = h;

    ctx.drawImage(video, 0, 0, w, h);

    try {
      // 1. Luminance & Lighting Calculation
      const imgData = ctx.getImageData(0, 0, w, h);
      const data = imgData.data;
      let totalLuminance = 0;
      const step = 4 * 4; // Sample every 4th pixel for high efficiency
      let sampleCount = 0;

      for (let i = 0; i < data.length; i += step) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        // Standard perceived luminance formula (ITU-R BT.601)
        const lum = 0.299 * r + 0.587 * g + 0.114 * b;
        totalLuminance += lum;
        sampleCount++;
      }

      const avgLuminance = sampleCount > 0 ? Math.round(totalLuminance / sampleCount) : 0;
      let lighting: 'good' | 'low' | 'bright' = 'good';
      let message = 'Good lighting & visibility';

      if (avgLuminance < 45) {
        lighting = 'low';
        message = 'Low lighting detected — consider turning on a front light';
      } else if (avgLuminance > 215) {
        lighting = 'bright';
        message = 'High glare / overexposure detected';
      }

      // 2. Native Shape Detection API (if supported by browser engine)
      let detectedFace: boolean | null = null;
      let centered: boolean | null = null;

      if (typeof window !== 'undefined' && 'FaceDetector' in window) {
        try {
          const FaceDetectorCtor = (window as any).FaceDetector;
          const detector = new FaceDetectorCtor({ fastMode: true, maxDetectedFaces: 1 });
          const faces = await detector.detect(canvas);

          if (faces && faces.length > 0) {
            detectedFace = true;
            const bbox = faces[0].boundingBox;
            const faceCenterX = bbox.x + bbox.width / 2;
            centered = faceCenterX >= w * 0.35 && faceCenterX <= w * 0.65;
            if (!centered) {
              message = 'Face detected — consider centering yourself in the frame';
            }
          } else {
            detectedFace = false;
            message = 'No face detected in center frame';
          }
        } catch (e) {
          // Native detector error fallback
          detectedFace = null;
        }
      }

      setMetrics({
        lightingQuality: lighting,
        luminanceScore: avgLuminance,
        faceDetected: detectedFace,
        isCentered: centered,
        feedbackMessage: message,
      });
    } catch (e) {
      // Ignored
    }
  }, []);

  // Start Camera Stream (Only called on explicit candidate button click!)
  const startCamera = async (deviceIdToUse?: string) => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      updateStatus('unsupported');
      setErrorMessage('Camera access is not supported in this browser.');
      return;
    }

    stopTracks();
    setErrorMessage(null);
    updateStatus('requesting');

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
          deviceId: deviceIdToUse ? { exact: deviceIdToUse } : undefined,
        },
        audio: false, // AUDIO NEVER REQUESTED HERE - Managed strictly by voice engine
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play().catch(() => {});
        };
      }

      // Listen for unexpected track ending (e.g. OS permissions revoked or device unplugged)
      const track = stream.getVideoTracks()[0];
      if (track) {
        track.onended = () => {
          stopTracks();
          updateStatus('disconnected');
          setErrorMessage('Video track ended.');
        };
      }

      updateStatus('active');
      await enumerateCameras();

      // Start periodic lightweight visual checks (every 1.5 seconds)
      if (analysisTimerRef.current) clearInterval(analysisTimerRef.current);
      analysisTimerRef.current = setInterval(runVisualChecks, 1500);
      runVisualChecks();
    } catch (err: any) {
      stopTracks();
      const errName = err.name || '';

      if (errName === 'NotAllowedError' || errName === 'PermissionDeniedError') {
        updateStatus('denied');
        setErrorMessage('Camera permission was denied. You can continue the voice interview without video.');
      } else if (errName === 'NotFoundError' || errName === 'DevicesNotFoundError') {
        updateStatus('unavailable');
        setErrorMessage('No camera was detected on this device.');
      } else if (errName === 'NotReadableError' || errName === 'TrackStartError') {
        updateStatus('unavailable');
        setErrorMessage('Camera is currently in use by another application.');
      } else {
        updateStatus('unavailable');
        setErrorMessage(`Camera error: ${err.message || 'Unable to access video stream'}`);
      }
    }
  };

  const handleDisableCamera = () => {
    stopTracks();
    updateStatus('disabled');
    setMetrics({
      lightingQuality: 'unknown',
      luminanceScore: 0,
      faceDetected: null,
      isCentered: null,
      feedbackMessage: 'Camera disabled',
    });
  };

  const handleSwitchCamera = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newDeviceId = e.target.value;
    setSelectedDeviceId(newDeviceId);
    if (status === 'active') {
      await startCamera(newDeviceId);
    }
  };

  return (
    <div
      className="p-5 bg-slate-900/90 border border-slate-800 rounded-3xl shadow-xl backdrop-blur-md space-y-4 select-none"
      role="region"
      aria-label="Candidate Optional Webcam Preview and Presence Checks"
    >
      {/* Header and Toggle Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>Candidate Camera Preview</span>
              <span className="text-[10px] font-medium px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                Optional
              </span>
            </h3>
            <p className="text-[11px] text-slate-400">Privacy-first • Zero video recording or upload</p>
          </div>
        </div>

        {status === 'active' ? (
          <button
            onClick={handleDisableCamera}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs font-medium transition cursor-pointer"
            aria-label="Turn off candidate camera"
          >
            <CameraOff className="w-3.5 h-3.5 text-rose-400" />
            <span>Turn Off</span>
          </button>
        ) : (
          <button
            onClick={() => startCamera(selectedDeviceId)}
            disabled={status === 'requesting'}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition cursor-pointer"
            aria-label="Enable candidate camera"
          >
            <Camera className="w-3.5 h-3.5" />
            <span>{status === 'requesting' ? 'Requesting...' : 'Enable Camera'}</span>
          </button>
        )}
      </div>

      {/* Video Viewport / Standby Card */}
      <div className="relative w-full aspect-video sm:aspect-[4/3] rounded-2xl bg-slate-950 border border-slate-800/80 overflow-hidden flex items-center justify-center">
        {status === 'active' ? (
          <>
            {/* Live Video Element */}
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover transform -scale-x-100"
              aria-label="Live Candidate Video Stream"
            />

            {/* Framing Guide Overlay (Subtle center oval for candidate eye-level positioning) */}
            <div
              className="absolute inset-0 pointer-events-none flex items-center justify-center"
              aria-hidden="true"
            >
              <div className="w-44 h-56 rounded-full border border-dashed border-indigo-400/25 opacity-70" />
            </div>

            {/* Privacy Watermark Badge */}
            <div className="absolute top-2.5 left-2.5 px-2 py-1 rounded-lg bg-slate-950/80 backdrop-blur-md border border-slate-800 flex items-center gap-1.5 text-[10px] text-slate-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Local Stream Only • Not Recorded</span>
            </div>
          </>
        ) : (
          /* Camera Inactive / Standby Empty State */
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2 text-slate-500">
            {status === 'denied' ? (
              <>
                <CameraOff className="w-8 h-8 text-rose-400" />
                <p className="text-xs font-semibold text-rose-300">Camera Permission Blocked</p>
                <p className="text-[11px] text-slate-400 max-w-xs">
                  Camera permission was denied. You can participate fully in the voice interview without video.
                </p>
              </>
            ) : status === 'unavailable' ? (
              <>
                <AlertTriangle className="w-8 h-8 text-amber-400" />
                <p className="text-xs font-semibold text-amber-300">Camera Unavailable</p>
                <p className="text-[11px] text-slate-400 max-w-xs">{errorMessage}</p>
              </>
            ) : status === 'requesting' ? (
              <>
                <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
                <p className="text-xs font-semibold text-indigo-300">Waiting for Camera Permission...</p>
                <p className="text-[11px] text-slate-400 max-w-xs">Please allow camera access in your browser prompt.</p>
              </>
            ) : (
              <>
                <VideoOff className="w-8 h-8 text-slate-600" />
                <p className="text-xs font-semibold text-slate-400">Webcam Inactive (Optional)</p>
                <p className="text-[11px] text-slate-500 max-w-xs">
                  Turn on your camera anytime to check your lighting, positioning, and framing during practice.
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Visual Presence & Quality Guidance Status Panel */}
      {status === 'active' && (
        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 text-xs">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Sun className="w-3.5 h-3.5 text-amber-400" />
              <span>Lighting:</span>
              <span
                className={`font-medium ${
                  metrics.lightingQuality === 'good'
                    ? 'text-emerald-400'
                    : metrics.lightingQuality === 'low'
                    ? 'text-amber-400'
                    : 'text-cyan-400'
                }`}
              >
                {metrics.lightingQuality === 'good'
                  ? 'Good'
                  : metrics.lightingQuality === 'low'
                  ? 'Low Light'
                  : 'Bright / Glare'}
              </span>
            </span>

            {/* Native Face Detection Indicator if supported */}
            {metrics.faceDetected !== null && (
              <span className="flex items-center gap-1 text-[11px]">
                {metrics.faceDetected ? (
                  <span className="text-emerald-400 flex items-center gap-1 font-medium">
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Face Visible</span>
                  </span>
                ) : (
                  <span className="text-amber-400 flex items-center gap-1 font-medium">
                    <UserX className="w-3.5 h-3.5" />
                    <span>Center in Frame</span>
                  </span>
                )}
              </span>
            )}
          </div>

          <p className="text-[11px] text-slate-400 leading-normal">{metrics.feedbackMessage}</p>

          {/* Multiple camera device switcher (if available) */}
          {availableCameras.length > 1 && (
            <div className="pt-1.5 border-t border-slate-800/80 flex items-center justify-between gap-2 text-[11px]">
              <label className="text-slate-400 font-medium shrink-0">Switch Camera:</label>
              <select
                value={selectedDeviceId}
                onChange={handleSwitchCamera}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-[11px] focus:outline-none focus:border-indigo-500"
              >
                {availableCameras.map((cam, idx) => (
                  <option key={cam.deviceId || idx} value={cam.deviceId}>
                    {cam.label || `Camera ${idx + 1}`}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Explicit Privacy Notice */}
      <div className="flex items-center gap-2 px-1 text-[11px] text-slate-400">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
        <span>100% In-Browser Preview • Never Recorded • Strictly ₹0 Cost</span>
      </div>
    </div>
  );
};
