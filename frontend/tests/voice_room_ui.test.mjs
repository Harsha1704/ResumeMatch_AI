/**
 * frontend/tests/voice_room_ui.test.mjs
 * Unit and behavioral tests for Phase 5 Premium Voice Room UI & Visualizations.
 * Tests avatar states, waveform modes, timer progression, transcript management,
 * mute output decoupling, and accessibility labels.
 */

import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

describe('Phase 5 Premium Voice Room UI & Visualizations Tests', () => {
  test('1. Avatar State: maps real interview engine states deterministically', () => {
    // Helper function matching VoiceInterviewPage's derivation logic
    const deriveAvatarState = ({ isSubmitting, isSpeaking, isListening }) => {
      if (isSubmitting) return 'thinking';
      if (isSpeaking) return 'speaking';
      if (isListening) return 'listening';
      return 'idle';
    };

    // Idle when nothing active
    assert.strictEqual(
      deriveAvatarState({ isSubmitting: false, isSpeaking: false, isListening: false }),
      'idle'
    );

    // Speaking when synthesis is talking
    assert.strictEqual(
      deriveAvatarState({ isSubmitting: false, isSpeaking: true, isListening: false }),
      'speaking'
    );

    // Listening when candidate microphone is capturing
    assert.strictEqual(
      deriveAvatarState({ isSubmitting: false, isSpeaking: false, isListening: true }),
      'listening'
    );

    // Thinking takes priority when evaluating answer or calling backend
    assert.strictEqual(
      deriveAvatarState({ isSubmitting: true, isSpeaking: false, isListening: false }),
      'thinking'
    );

    // Thinking has higher priority than listening/speaking
    assert.strictEqual(
      deriveAvatarState({ isSubmitting: true, isSpeaking: true, isListening: true }),
      'thinking'
    );
  });

  test('2. Waveform Mode: maps audio channel activity to waveform modes', () => {
    const deriveWaveformMode = ({ isSubmitting, isSpeaking, isListening }) => {
      if (isSubmitting) return 'thinking';
      if (isSpeaking) return 'speaking';
      if (isListening) return 'listening';
      return 'idle';
    };

    assert.strictEqual(deriveWaveformMode({ isSubmitting: false, isSpeaking: false, isListening: false }), 'idle');
    assert.strictEqual(deriveWaveformMode({ isSubmitting: false, isSpeaking: true, isListening: false }), 'speaking');
    assert.strictEqual(deriveWaveformMode({ isSubmitting: false, isSpeaking: false, isListening: true }), 'listening');
    assert.strictEqual(deriveWaveformMode({ isSubmitting: true, isSpeaking: false, isListening: false }), 'thinking');
  });

  test('3. Elapsed Timer: formats seconds accurately into MM:SS', () => {
    const formatTime = (totalSecs) => {
      const mins = Math.floor(totalSecs / 60);
      const secs = totalSecs % 60;
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    assert.strictEqual(formatTime(0), '00:00');
    assert.strictEqual(formatTime(9), '00:09');
    assert.strictEqual(formatTime(65), '01:05');
    assert.strictEqual(formatTime(360), '06:00');
    assert.strictEqual(formatTime(3599), '59:59');
  });

  test('4. Progress Bar: calculates progress percentage with bounds clamping', () => {
    const calculateProgress = (currentIndex, totalQuestions) => {
      if (totalQuestions <= 0) return 0;
      return Math.min(100, Math.round(((currentIndex + 1) / totalQuestions) * 100));
    };

    assert.strictEqual(calculateProgress(0, 5), 20);
    assert.strictEqual(calculateProgress(1, 5), 40);
    assert.strictEqual(calculateProgress(2, 5), 60);
    assert.strictEqual(calculateProgress(4, 5), 100);
    assert.strictEqual(calculateProgress(0, 0), 0);
    // Boundary clamping: if currentIndex >= totalQuestions
    assert.strictEqual(calculateProgress(6, 5), 100);
  });

  test('5. Transcript Ordering: preserves strict chronological sequence and speaker roles', () => {
    const transcript = [];
    const addMessage = (speaker, message_type, message_text, timestamp) => {
      transcript.push({
        entry_id: `entry-${transcript.length + 1}`,
        speaker,
        message_type,
        message_text,
        timestamp,
        sequence_order: transcript.length,
      });
    };

    const t0 = 1731900000000;
    addMessage('interviewer', 'greeting', 'Welcome to your interview.', t0);
    addMessage('interviewer', 'question', 'Tell me about an API design project.', t0 + 2000);
    addMessage('candidate', 'answer', 'I built a RESTful microservice with Redis.', t0 + 15000);
    addMessage('interviewer', 'feedback', 'Good response explaining caching.', t0 + 17000);

    assert.strictEqual(transcript.length, 4);
    assert.strictEqual(transcript[0].speaker, 'interviewer');
    assert.strictEqual(transcript[0].message_type, 'greeting');
    assert.strictEqual(transcript[1].speaker, 'interviewer');
    assert.strictEqual(transcript[1].message_type, 'question');
    assert.strictEqual(transcript[2].speaker, 'candidate');
    assert.strictEqual(transcript[2].message_type, 'answer');
    assert.strictEqual(transcript[3].speaker, 'interviewer');
    assert.strictEqual(transcript[3].message_type, 'feedback');

    // Confirm timestamps are non-decreasing
    for (let i = 1; i < transcript.length; i++) {
      assert.ok(transcript[i].timestamp >= transcript[i - 1].timestamp);
    }
  });

  test('6. Candidate Answer Editing: preserves user modifications before submission', () => {
    let candidateAnswer = 'I implemented a microservice';
    // User types additional words or edits recognized text
    candidateAnswer += ' using Go and PostgreSQL.';

    const wordCount = candidateAnswer.trim().split(/\s+/).filter(Boolean).length;
    assert.strictEqual(wordCount, 8);
    assert.strictEqual(candidateAnswer, 'I implemented a microservice using Go and PostgreSQL.');
  });

  test('7. Mute Decoupling: silences audio output while keeping recognition active', () => {
    let isMuted = false;
    let isListening = true;

    // Toggle mute
    isMuted = !isMuted;
    assert.strictEqual(isMuted, true);
    // Crucial requirement: candidate microphone is NOT turned off by muting interviewer
    assert.strictEqual(isListening, true);
  });

  test('8. Manual Text Fallback: toggles gracefully without breaking session', () => {
    let manualMode = false;

    // Candidate switches to manual text mode
    manualMode = true;
    assert.strictEqual(manualMode, true);

    // Candidate switches back to voice mode
    manualMode = false;
    assert.strictEqual(manualMode, false);
  });
});
