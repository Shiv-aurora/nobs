class PCM16Processor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.pending = [];
    }

    process(inputs) {
        const input = inputs[0] && inputs[0][0];
        if (!input) {
            return true;
        }

        const ratio = sampleRate / 16000;
        const length = Math.max(1, Math.floor(input.length / ratio));
        for (let index = 0; index < length; index += 1) {
            const sample = Math.max(-1, Math.min(1, input[Math.floor(index * ratio)] || 0));
            this.pending.push(sample < 0 ? sample * 32768 : sample * 32767);
        }

        // 480 samples is 30 ms at 16 kHz. Transfer ownership of each frame so
        // the UI thread does not retain or copy meeting audio.
        while (this.pending.length >= 480) {
            const pcm = Int16Array.from(this.pending.splice(0, 480));
            this.port.postMessage(pcm.buffer, [pcm.buffer]);
        }
        return true;
    }
}

registerProcessor('nobs-pcm16', PCM16Processor);
