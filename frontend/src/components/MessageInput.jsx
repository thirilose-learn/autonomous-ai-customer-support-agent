import React, { useState, useRef, useEffect } from 'react';
import { transcribeAudio } from '../services/api';

export function MessageInput({ onSendMessage, disabled }) {
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voiceError, setVoiceError] = useState(null);

  const textareaRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const isCancelledRef = useRef(false);

  // Auto-resize textarea based on content and control scrollbar visibility
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 120)}px`;
      textareaRef.current.style.overflowY = scrollHeight > 120 ? 'auto' : 'hidden';
    }
  }, [inputText]);

  // Clean up recording timer and audio tracks on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const handleSubmit = (e) => {
    if (e && e.preventDefault) {
      e.preventDefault();
    }
    if (!inputText.trim() || disabled || isRecording || isTranscribing) return;
    onSendMessage(inputText.trim());
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.overflowY = 'hidden';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Shift + Enter: Allow default newline in textarea
        return;
      }
      // Enter: Send message immediately
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Start Voice Recording via MediaRecorder
  const startRecording = async () => {
    setVoiceError(null);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setVoiceError('Microphone recording is not supported in this browser.');
      return;
    }

    try {
      isCancelledRef.current = false;
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Select supported audio MIME type
      let options = { mimeType: 'audio/webm' };
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          options = { mimeType: 'audio/webm;codecs=opus' };
        } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
          options = { mimeType: 'audio/ogg;codecs=opus' };
        } else {
          options = {}; // browser default
        }
      }

      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Stop audio hardware tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }

        if (isCancelledRef.current) {
          audioChunksRef.current = [];
          setIsRecording(false);
          setRecordingSeconds(0);
          return;
        }

        const mime = audioChunksRef.current[0]?.type || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mime });
        audioChunksRef.current = [];
        setIsRecording(false);
        setRecordingSeconds(0);

        if (audioBlob.size < 200) {
          setVoiceError('Recording was too short. Please speak clearly and try again.');
          return;
        }

        // Send to backend Whisper endpoint
        setIsTranscribing(true);
        try {
          const result = await transcribeAudio(audioBlob);
          if (result && result.text && result.text.trim()) {
            setInputText((prev) => {
              const cleaned = prev.trim();
              return cleaned ? `${cleaned} ${result.text.trim()}` : result.text.trim();
            });
            if (textareaRef.current) {
              textareaRef.current.focus();
            }
          } else {
            setVoiceError('No speech was detected in the recording. Please try again.');
          }
        } catch (err) {
          setVoiceError(err.message || 'Speech transcription failed. Please try again.');
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((sec) => sec + 1);
      }, 1000);
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setVoiceError('Microphone permission was denied. Please allow microphone access in your browser settings.');
      } else if (err.name === 'NotFoundError') {
        setVoiceError('No microphone was found on this device.');
      } else {
        setVoiceError(`Could not access microphone: ${err.message || 'Unknown error'}`);
      }
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
  };

  const cancelRecording = () => {
    isCancelledRef.current = true;
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
  };

  const formatSeconds = (sec) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="chat-input-area">
      {voiceError && (
        <div className="voice-alert-banner" role="alert">
          <div className="voice-alert-content">
            <span className="voice-alert-icon" aria-hidden="true">⚠️</span>
            <span>{voiceError}</span>
          </div>
          <button
            type="button"
            className="voice-alert-close"
            onClick={() => setVoiceError(null)}
            title="Dismiss error"
            aria-label="Dismiss alert"
          >
            &times;
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className={`input-box-wrapper ${isRecording ? 'recording-active' : ''}`}>
          <textarea
            ref={textareaRef}
            rows={1}
            className="chat-input"
            placeholder={
              isRecording
                ? `Listening to your voice... (${formatSeconds(recordingSeconds)})`
                : isTranscribing
                ? 'Whisper is transcribing your speech...'
                : 'Type or speak your support inquiry (e.g. "Where is my order?")...'
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isTranscribing}
            autoComplete="off"
            aria-label="Customer inquiry input"
          />

          <div className="input-actions-group">
            {isRecording && (
              <button
                type="button"
                className="cancel-record-inline-btn"
                onClick={cancelRecording}
                title="Cancel voice recording"
                aria-label="Cancel recording"
              >
                Cancel
              </button>
            )}

            <button
              type="button"
              className={`voice-mic-btn ${isRecording ? 'recording' : ''} ${isTranscribing ? 'transcribing' : ''}`}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={disabled || isTranscribing}
              title={
                isRecording
                  ? `Recording (${formatSeconds(recordingSeconds)}) — Click to stop and transcribe`
                  : isTranscribing
                  ? 'Transcribing audio with Whisper...'
                  : 'Voice input with Whisper'
              }
              aria-label={isRecording ? 'Stop recording' : 'Start voice input with Whisper'}
            >
              {isTranscribing ? (
                <span className="btn-spinner" aria-hidden="true"></span>
              ) : isRecording ? (
                <span className="recording-stop-icon" aria-hidden="true">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="4" y="4" width="16" height="16" rx="2"></rect>
                  </svg>
                </span>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="23"></line>
                  <line x1="8" y1="23" x2="16" y2="23"></line>
                </svg>
              )}
            </button>

            <button
              type="submit"
              className="send-btn"
              disabled={disabled || !inputText.trim() || isRecording || isTranscribing}
              title="Send message (Enter)"
              aria-label="Send message"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>
      </form>

      <div className="input-footer-note">
        <span>Enter to send &bull; Shift + Enter for new line</span>
        <span>🎙️ Whisper Voice Ready</span>
      </div>
    </div>
  );
}

export default MessageInput;

