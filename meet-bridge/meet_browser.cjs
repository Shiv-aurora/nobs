'use strict';

const path = require('path');

function loadPlaywright() {
    try {
        return require('playwright');
    } catch (_) {
        return require(path.resolve(__dirname, '../e2e/node_modules/playwright'));
    }
}

const {chromium} = loadPlaywright();
const job = JSON.parse(process.env.NOPING_MEET_JOB || '{}');
const profileDir = process.env.NOPING_MEET_PROFILE_DIR || path.resolve(__dirname, '.chrome-profile');
const headless = /^(1|true|yes)$/i.test(process.env.NOPING_MEET_HEADLESS || 'false');
const channel = process.env.NOPING_MEET_CHROME_CHANNEL || 'chrome';

function emit(payload) {
    process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function validMeetURL(value) {
    try {
        const parsed = new URL(value);
        return parsed.protocol === 'https:' && parsed.hostname === 'meet.google.com';
    } catch (_) {
        return false;
    }
}

async function firstVisible(locators, timeout = 30000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
        for (const locator of locators) {
            if (await locator.isVisible().catch(() => false)) {
                return locator;
            }
        }
        await new Promise((resolve) => setTimeout(resolve, 350));
    }
    return null;
}

async function main() {
    if (!validMeetURL(job.conference_uri)) {
        throw new Error('The bridge accepts only validated https://meet.google.com URLs');
    }
    if (!job.participant_display_name) {
        throw new Error('A disclosed participant display name is required');
    }

    const context = await chromium.launchPersistentContext(profileDir, {
        channel,
        headless,
        permissions: ['microphone', 'camera'],
        args: [
            '--autoplay-policy=no-user-gesture-required',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--use-fake-ui-for-media-stream',
        ],
    });
    const pages = context.pages();
    const page = pages[0] || await context.newPage();

    await page.exposeBinding('__nobsAudioIn', async (_source, encoded) => {
        emit({audio_in: encoded});
    });
    await page.addInitScript(() => {
        const state = {
            outputContext: null,
            outputDestination: null,
            nextOutputAt: 0,
            captureTracks: new WeakSet(),
        };
        const encode = (bytes) => {
            let binary = '';
            const step = 0x8000;
            for (let index = 0; index < bytes.length; index += step) {
                binary += String.fromCharCode(...bytes.subarray(index, index + step));
            }
            return btoa(binary);
        };
        const decode = (value) => {
            const binary = atob(value);
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {
                bytes[index] = binary.charCodeAt(index);
            }
            return bytes;
        };
        const ensureOutput = () => {
            if (!state.outputContext) {
                state.outputContext = new AudioContext({sampleRate: 24000});
                state.outputDestination = state.outputContext.createMediaStreamDestination();
                state.nextOutputAt = state.outputContext.currentTime;
            }
            return state;
        };
        window.__nobsPlayPcm16 = async (encoded) => {
            const current = ensureOutput();
            await current.outputContext.resume();
            const bytes = decode(encoded);
            const samples = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.byteLength / 2));
            const buffer = current.outputContext.createBuffer(1, samples.length, 24000);
            const channelData = buffer.getChannelData(0);
            for (let index = 0; index < samples.length; index += 1) {
                channelData[index] = samples[index] / 32768;
            }
            const source = current.outputContext.createBufferSource();
            source.buffer = buffer;
            source.connect(current.outputDestination);
            const startAt = Math.max(current.outputContext.currentTime, current.nextOutputAt);
            current.nextOutputAt = startAt + buffer.duration;
            source.start(startAt);
        };
        const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        navigator.mediaDevices.getUserMedia = async (constraints = {}) => {
            if (!constraints.audio) {
                return originalGetUserMedia(constraints);
            }
            const current = ensureOutput();
            let stream = new MediaStream();
            if (constraints.video) {
                try {
                    stream = await originalGetUserMedia({...constraints, audio: false});
                } catch (_) {
                    stream = new MediaStream();
                }
            }
            for (const track of current.outputDestination.stream.getAudioTracks()) {
                stream.addTrack(track);
            }
            return stream;
        };
        const captureTrack = async (track) => {
            if (!track || track.kind !== 'audio' || state.captureTracks.has(track)) {
                return;
            }
            state.captureTracks.add(track);
            const context = new AudioContext({sampleRate: 16000});
            const source = context.createMediaStreamSource(new MediaStream([track]));
            const processor = context.createScriptProcessor(4096, 1, 1);
            const muted = context.createGain();
            muted.gain.value = 0;
            processor.onaudioprocess = (event) => {
                const input = event.inputBuffer.getChannelData(0);
                const pcm = new Int16Array(input.length);
                for (let index = 0; index < input.length; index += 1) {
                    const sample = Math.max(-1, Math.min(1, input[index]));
                    pcm[index] = sample < 0 ? sample * 32768 : sample * 32767;
                }
                void window.__nobsAudioIn(encode(new Uint8Array(pcm.buffer)));
            };
            source.connect(processor);
            processor.connect(muted);
            muted.connect(context.destination);
            await context.resume();
        };
        const NativePeerConnection = window.RTCPeerConnection;
        if (NativePeerConnection) {
            const WrappedPeerConnection = new Proxy(NativePeerConnection, {
                construct(Target, args) {
                    const peer = Reflect.construct(Target, args);
                    peer.addEventListener('track', (event) => void captureTrack(event.track));
                    return peer;
                },
            });
            window.RTCPeerConnection = WrappedPeerConnection;
            if (window.webkitRTCPeerConnection) {
                window.webkitRTCPeerConnection = WrappedPeerConnection;
            }
        }
    });

    process.stdin.setEncoding('utf8');
    let buffered = '';
    process.stdin.on('data', (chunk) => {
        buffered += chunk;
        let newline = buffered.indexOf('\n');
        while (newline >= 0) {
            const line = buffered.slice(0, newline);
            buffered = buffered.slice(newline + 1);
            try {
                const message = JSON.parse(line);
                if (message.audio_out) {
                    void page.evaluate((audio) => window.__nobsPlayPcm16(audio), message.audio_out).catch(() => undefined);
                }
            } catch (_) {
                // Ignore malformed local IPC; the signed media session remains authoritative.
            }
            newline = buffered.indexOf('\n');
        }
    });

    emit({status: 'joining'});
    await page.goto(job.conference_uri, {waitUntil: 'domcontentloaded', timeout: 60000});
    if (page.url().includes('accounts.google.com')) {
        emit({notice: 'Sign in to the dedicated NoBS Agent Google account in the opened Chrome window.'});
        await page.waitForURL((url) => url.hostname === 'meet.google.com', {timeout: 10 * 60 * 1000});
    }

    const nameInput = await firstVisible([
        page.getByRole('textbox', {name: /your name/i}),
        page.locator('input[placeholder*="name" i]'),
    ], 5000);
    if (nameInput) {
        await nameInput.fill(job.participant_display_name);
    }

    const cameraButton = await firstVisible([
        page.getByRole('button', {name: /turn off camera/i}),
        page.getByRole('button', {name: /camera.*on/i}),
    ], 3000);
    if (cameraButton) {
        await cameraButton.click().catch(() => undefined);
    }

    const joinButton = await firstVisible([
        page.getByRole('button', {name: /^join now$/i}),
        page.getByRole('button', {name: /^ask to join$/i}),
        page.getByRole('button', {name: /^join$/i}),
    ], 60000);
    if (!joinButton) {
        throw new Error('Google Meet did not expose a Join now or Ask to join action');
    }
    const joinLabel = (await joinButton.innerText()).trim();
    await joinButton.click();
    if (/ask to join/i.test(joinLabel)) {
        emit({status: 'awaiting_admission'});
    }

    const leaveButton = await firstVisible([
        page.getByRole('button', {name: /leave call/i}),
        page.getByRole('button', {name: /end call/i}),
    ], 5 * 60 * 1000);
    if (!leaveButton) {
        throw new Error('The host did not admit the NoBS Agent before the admission window expired');
    }
    emit({status: 'live', participant_display_name: job.participant_display_name});

    while (!page.isClosed() && await leaveButton.isVisible().catch(() => false)) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    emit({status: 'ended'});
    await context.close();
}

main().catch((error) => {
    emit({status: 'failed', error: String(error && error.message ? error.message : error)});
    process.exitCode = 1;
});
