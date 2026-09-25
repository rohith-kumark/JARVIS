/**
 * AudioStreamer: Manages Web Audio API microphone capture (16kHz PCM)
 * and seamless audio response playback (24kHz PCM) with instant barge-in interruption.
 */

export class AudioStreamer {
  constructor({ onAudioChunk, onError }) {
    this.onAudioChunk = onAudioChunk; // Callback receiving base64 16kHz PCM chunks
    this.onError = onError;

    this.audioContext = null;
    this.mediaStream = null;
    this.sourceNode = null;
    this.processorNode = null;

    // Playback state
    this.playbackContext = null;
    this.activeSourceNodes = new Set();
    this.nextScheduledTime = 0;
    this.isRecording = false;
  }

  /**
   * Request microphone access and start streaming 16kHz 16-bit PCM chunks.
   */
  async startRecording() {
    try {
      if (this.isRecording) return;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioCtx({ sampleRate: 16000 });

      // Request microphone stream
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Buffer size: 2048 samples at 16kHz ~= 128ms per chunk
      const bufferSize = 2048;
      this.processorNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

      this.processorNode.onaudioprocess = (e) => {
        if (!this.isRecording) return;
        const inputData = e.inputBuffer.getChannelData(0);

        // Convert Float32 [-1.0, 1.0] to 16-bit signed PCM [-32768, 32767]
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Convert Int16Array to binary base64
        const uint8 = new Uint8Array(pcm16.buffer);
        let binary = "";
        const len = uint8.byteLength;
        for (let i = 0; i < len; i++) {
          binary += String.fromCharCode(uint8[i]);
        }
        const b64Data = window.btoa(binary);

        if (this.onAudioChunk) {
          this.onAudioChunk(b64Data);
        }
      };

      this.sourceNode.connect(this.processorNode);
      this.processorNode.connect(this.audioContext.destination);

      // Initialize playback context at 24kHz for native Gemini output
      if (!this.playbackContext || this.playbackContext.state === "closed") {
        this.playbackContext = new AudioCtx({ sampleRate: 24000 });
      } else if (this.playbackContext.state === "suspended") {
        await this.playbackContext.resume();
      }
      this.nextScheduledTime = this.playbackContext.currentTime;

      this.isRecording = true;
    } catch (err) {
      const msg = err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
        ? "Microphone permission is required to enable voice interaction."
        : `Microphone access failure: ${err.message || err}`;
      if (this.onError) this.onError(msg);
      throw new Error(msg);
    }
  }

  /**
   * Schedule and play an incoming 24kHz 16-bit PCM chunk smoothly.
   */
  playChunk(base64Pcm, sampleRate = 24000) {
    if (!base64Pcm) return;

    try {
      if (!this.playbackContext || this.playbackContext.state === "closed") {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.playbackContext = new AudioCtx({ sampleRate });
      }

      if (this.playbackContext.state === "suspended") {
        this.playbackContext.resume();
      }

      // Decode base64 to raw bytes
      const binaryString = window.atob(base64Pcm);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Convert 16-bit PCM to Float32
      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      // Create Web Audio buffer
      const audioBuffer = this.playbackContext.createBuffer(1, float32Array.length, sampleRate);
      audioBuffer.copyToChannel(float32Array, 0);

      // Create buffer source
      const source = this.playbackContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.playbackContext.destination);

      const currentTime = this.playbackContext.currentTime;
      // Schedule chunk seamlessly back-to-back
      const startTime = Math.max(currentTime, this.nextScheduledTime);
      source.start(startTime);
      this.nextScheduledTime = startTime + audioBuffer.duration;

      this.activeSourceNodes.add(source);
      source.onended = () => {
        this.activeSourceNodes.delete(source);
      };
    } catch (err) {
      console.warn("Error playing audio chunk:", err);
    }
  }

  /**
   * Barge-in interruption: immediately halt and cancel all playing/scheduled audio.
   */
  interrupt() {
    for (const source of this.activeSourceNodes) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Source may already have ended
      }
    }
    this.activeSourceNodes.clear();

    if (this.playbackContext) {
      this.nextScheduledTime = this.playbackContext.currentTime;
    }
  }

  /**
   * Stop recording and release all audio resources.
   */
  stopRecording() {
    this.isRecording = false;

    if (this.processorNode) {
      try {
        this.processorNode.disconnect();
      } catch {}
      this.processorNode = null;
    }

    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {}
      this.sourceNode = null;
    }

    if (this.mediaStream) {
      try {
        this.mediaStream.getTracks().forEach((track) => track.stop());
      } catch {}
      this.mediaStream = null;
    }

    if (this.audioContext && this.audioContext.state !== "closed") {
      try {
        this.audioContext.close();
      } catch {}
      this.audioContext = null;
    }

    this.interrupt();
  }
}
