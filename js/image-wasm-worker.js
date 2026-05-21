self.onmessage = async function(event) {
    const message = event.data || {};
    if (message.type !== 'process') return;

    try {
        const assetVersion = new URL(self.location.href).searchParams.get('v') || '20260521-tcloud1';
        const wasmModuleUrl = new URL('../wasm/hilbert_image_cipher_wasm.js', self.location.href);
        const wasmBinaryUrl = new URL('../wasm/hilbert_image_cipher_wasm_bg.wasm', self.location.href);
        wasmModuleUrl.searchParams.set('v', assetVersion);
        wasmBinaryUrl.searchParams.set('v', assetVersion);

        const wasm = await import(wasmModuleUrl.href);
        const wasmResponse = await fetch(wasmBinaryUrl.href, { cache: 'force-cache' });
        await wasm.default(wasmResponse);

        const method = message.method === 'block' ? wasm.CipherMethod.Block : wasm.CipherMethod.Gilbert;
        const mode = message.mode === 'decrypt' ? wasm.CipherMode.Decrypt : wasm.CipherMode.Encrypt;
        const input = new Uint8Array(message.dataBuffer);
        const output = wasm.process_rgba_rounds(
            input,
            message.width,
            message.height,
            method,
            mode,
            message.key || '',
            Math.max(1, message.blockW || 1),
            Math.max(1, message.blockH || 1),
            Math.max(1, message.rounds || 1),
            !!message.applyXor
        );

        self.postMessage({
            id: message.id,
            ok: true,
            buffer: output.buffer
        }, [output.buffer]);
    } catch (error) {
        self.postMessage({
            id: message.id,
            ok: false,
            error: error && error.message ? error.message : String(error)
        });
    }
};
