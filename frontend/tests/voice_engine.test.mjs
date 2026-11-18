/**
 * frontend/tests/voice_engine.test.mjs
 * Unit tests for Phase 4 Browser Voice Engine & Audio Controls.
 * Strict ₹0 Budget: Web Speech API (SpeechRecognition + SpeechSynthesis) and API client.
 */

import { test, beforeEach, describe } from 'node:test';
import assert from 'node:assert/strict';
import { SpeechRecognitionService } from '../src/services/speechRecognitionService.ts';
import { SpeechSynthesisService } from '../src/services/speechSynthesisService.ts';
import { api, clearCsrfToken } from '../src/services/api.ts';

describe('Phase 4 Browser Voice Engine Tests', () => {
  beforeEach(() => {
    clearCsrfToken();
    delete globalThis.window;
    delete globalThis.SpeechRecognition;
    delete globalThis.webkitSpeechRecognition;
    delete globalThis.speechSynthesis;
    delete globalThis.SpeechSynthesisUtterance;
  });

  test('1. Capability Detection: accurately reports unsupported when Web Speech API is absent', () => {
    assert.strictEqual(SpeechRecognitionService.isSupported(), false);
    assert.strictEqual(SpeechRecognitionService.getEngineName(), 'none');
    assert.strictEqual(SpeechSynthesisService.isSupported(), false);
  });

  test('2. Capability Detection: detects standard SpeechRecognition', () => {
    globalThis.SpeechRecognition = class MockSpeechRecognition {};
    globalThis.window = { SpeechRecognition: globalThis.SpeechRecognition };

    assert.strictEqual(SpeechRecognitionService.isSupported(), true);
    assert.strictEqual(SpeechRecognitionService.getEngineName(), 'SpeechRecognition');
  });

  test('3. Capability Detection: detects webkitSpeechRecognition prefix', () => {
    globalThis.webkitSpeechRecognition = class MockWebkitRecognition {};
    globalThis.window = { webkitSpeechRecognition: globalThis.webkitSpeechRecognition };

    assert.strictEqual(SpeechRecognitionService.isSupported(), true);
    assert.strictEqual(SpeechRecognitionService.getEngineName(), 'webkitSpeechRecognition');
  });

  test('4. Capability Detection: detects window.speechSynthesis', () => {
    class MockUtterance {}
    globalThis.SpeechSynthesisUtterance = MockUtterance;
    globalThis.window = {
      speechSynthesis: {
        speak: () => {},
        cancel: () => {},
        pause: () => {},
        resume: () => {},
        getVoices: () => [],
      },
      SpeechSynthesisUtterance: MockUtterance,
    };

    assert.strictEqual(SpeechSynthesisService.isSupported(), true);
  });

  test('5. SpeechRecognitionService: dispatches interim and final transcripts properly', async () => {
    let capturedInterim = '';
    let capturedFinal = '';

    class MockRecognition {
      constructor() {
        this.continuous = false;
        this.interimResults = false;
        this.lang = '';
        this.onresult = null;
        this.onerror = null;
        this.onend = null;
        this.onstart = null;
      }
      start() {
        if (this.onstart) this.onstart();
      }
      stop() {
        if (this.onend) this.onend();
      }
      abort() {}
    }

    globalThis.SpeechRecognition = MockRecognition;
    globalThis.window = { SpeechRecognition: MockRecognition };

    const service = new SpeechRecognitionService({
      onInterimTranscript: (interim) => {
        capturedInterim = interim;
      },
      onFinalTranscript: (final) => {
        capturedFinal = final;
      },
    });

    await service.startListening();
    assert.strictEqual(service.isListeningState(), true);

    // Simulate result event with interim item and final item
    const mockEvent = {
      resultIndex: 0,
      results: [
        Object.assign([{ transcript: 'I designed a scalable microservices architecture ' }], { isFinal: true }),
        Object.assign([{ transcript: 'using distributed caching' }], { isFinal: false }),
      ],
    };

    service.getRecognitionInstance().onresult(mockEvent);

    assert.strictEqual(capturedFinal, 'I designed a scalable microservices architecture');
    assert.strictEqual(capturedInterim, 'using distributed caching');

    service.stopListening();
    assert.strictEqual(service.isListeningState(), false);
  });

  test('6. SpeechRecognitionService: handles permission denial and error status codes', async () => {
    let capturedError = null;
    let isDenied = false;

    class MockRecognition {
      start() {}
      stop() {}
      abort() {}
    }

    globalThis.SpeechRecognition = MockRecognition;
    globalThis.window = { SpeechRecognition: MockRecognition };

    const service = new SpeechRecognitionService({
      onError: (err, denied) => {
        capturedError = err;
        isDenied = denied;
      },
    });

    await service.startListening();

    // Simulate permission denied error
    service.getRecognitionInstance().onerror({ error: 'not-allowed', message: 'User denied microphone' });

    assert.ok(capturedError.includes('Microphone permission was denied'));
    assert.strictEqual(isDenied, true);
    assert.strictEqual(service.getStatus(), 'error');
  });

  test('7. SpeechSynthesisService: speaks utterance and manages audio queue', async () => {
    let spokenText = '';
    let cancelCalled = false;
    let statusHistory = [];

    class MockUtterance {
      constructor(text) {
        this.text = text;
        this.rate = 1.0;
        this.pitch = 1.0;
        this.volume = 1.0;
        this.voice = null;
        this.onstart = null;
        this.onend = null;
        this.onerror = null;
      }
    }

    const mockSynth = {
      speaking: false,
      paused: false,
      cancel: () => {
        cancelCalled = true;
        mockSynth.speaking = false;
      },
      speak: (utt) => {
        spokenText = utt.text;
        mockSynth.speaking = true;
        if (utt.onstart) utt.onstart();
        setTimeout(() => {
          mockSynth.speaking = false;
          if (utt.onend) utt.onend();
        }, 5);
      },
      pause: () => { mockSynth.paused = true; },
      resume: () => { mockSynth.paused = false; },
      getVoices: () => [{ name: 'Alex', lang: 'en-US', default: true }],
    };

    globalThis.SpeechSynthesisUtterance = MockUtterance;
    globalThis.window = {
      speechSynthesis: mockSynth,
      SpeechSynthesisUtterance: MockUtterance,
    };

    const synthService = new SpeechSynthesisService({
      onStatusChange: (status) => statusHistory.push(status),
    });

    await synthService.speak('Welcome to your AI Voice Interview session.');

    assert.strictEqual(cancelCalled, true, 'SpeechSynthesisService must cancel pending audio before speaking');
    assert.strictEqual(spokenText, 'Welcome to your AI Voice Interview session.');
  });

  test('8. SpeechSynthesisService: Mute silences interviewer audio output without throwing', async () => {
    let speakCalled = false;

    class MockUtterance {
      constructor(t) { this.text = t; }
    }
    globalThis.SpeechSynthesisUtterance = MockUtterance;
    globalThis.window = {
      speechSynthesis: {
        speaking: true,
        cancel: () => {},
        speak: () => { speakCalled = true; },
        pause: () => {},
        resume: () => {},
        getVoices: () => [],
      },
      SpeechSynthesisUtterance: MockUtterance,
    };

    const synthService = new SpeechSynthesisService();
    assert.strictEqual(synthService.isMutedState(), false);

    synthService.setMuted(true);
    assert.strictEqual(synthService.isMutedState(), true);

    // When muted, speak() resolves immediately without queueing browser audio
    await synthService.speak('This should not make any noise');
    assert.strictEqual(speakCalled, false);
  });

  test('9. SpeechSynthesisService: Replays last spoken prompt cleanly', async () => {
    let lastSpoken = '';

    class MockUtterance {
      constructor(t) {
        this.text = t;
        this.onstart = null;
        this.onend = null;
      }
    }
    const mockSynth = {
      speaking: false,
      cancel: () => {},
      speak: (utt) => {
        lastSpoken = utt.text;
        if (utt.onstart) utt.onstart();
        setTimeout(() => {
          if (utt.onend) utt.onend();
        }, 5);
      },
      pause: () => {},
      resume: () => {},
      getVoices: () => [],
    };

    globalThis.SpeechSynthesisUtterance = MockUtterance;
    globalThis.window = {
      speechSynthesis: mockSynth,
      SpeechSynthesisUtterance: MockUtterance,
    };

    const synthService = new SpeechSynthesisService();
    await synthService.speak('Tell me about a time you optimized an API.');
    assert.strictEqual(lastSpoken, 'Tell me about a time you optimized an API.');

    await synthService.replay();
    assert.strictEqual(lastSpoken, 'Tell me about a time you optimized an API.');
  });

  test('10. API Client: Voice endpoints serialize payloads and use CSRF protection', async () => {
    const fetchRequests = [];

    globalThis.fetch = async (url, options = {}) => {
      fetchRequests.push({ url, options });

      if (url.includes('/api/csrf-token')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ status: 'success', csrf_token: 'test-csrf-token-xyz' }),
        };
      }

      if (url.includes('/api/interview/voice/start')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: 'success',
            session_id: 'session-voice-123',
            target_role: 'Backend Engineer',
            total_questions: 3,
            interviewer_speech: 'Hello candidate!',
            provider: 'local_heuristic_engine',
            budget: 'INR_0_FREE',
          }),
        };
      }

      if (url.includes('/api/interview/voice/answer')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: 'success',
            session_id: 'session-voice-123',
            interviewer_reaction: 'Great job detailing your approach.',
            has_adaptive_followup: false,
            is_last_question: false,
          }),
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success' }),
      };
    };

    // Test startVoiceSession
    const startRes = await api.startVoiceSession({
      target_role: 'Backend Engineer',
      difficulty: 'medium',
      max_questions: 3,
    });

    assert.strictEqual(startRes.session_id, 'session-voice-123');
    assert.strictEqual(startRes.provider, 'local_heuristic_engine');

    // Verify CSRF token and method
    const startReq = fetchRequests.find(r => r.url.includes('/api/interview/voice/start'));
    assert.ok(startReq, 'Must call /api/interview/voice/start');
    assert.strictEqual(startReq.options.method, 'POST');
    assert.strictEqual(startReq.options.headers['X-CSRF-Token'], 'test-csrf-token-xyz');

    // Test submitVoiceAnswer
    const answerRes = await api.submitVoiceAnswer('session-voice-123', 0, 'I implemented Redis caching.');
    assert.strictEqual(answerRes.status, 'success');
    assert.strictEqual(answerRes.interviewer_reaction, 'Great job detailing your approach.');

    const answerReq = fetchRequests.find(r => r.url.includes('/api/interview/voice/answer'));
    assert.ok(answerReq, 'Must call /api/interview/voice/answer');
    const body = JSON.parse(answerReq.options.body);
    assert.strictEqual(body.session_id, 'session-voice-123');
    assert.strictEqual(body.question_index, 0);
    assert.strictEqual(body.answer_text, 'I implemented Redis caching.');
  });
});
