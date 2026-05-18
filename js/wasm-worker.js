// WASM Worker — off-main-thread pixel processing
// Module worker (type: "module") so dynamic import() works
let wasmMod = null;
let nextJobId = 1;
const pending = new Map();

async function ensureWasm() {
  if (wasmMod) return wasmMod;
  const mod = await import('../wasm/hilbert_image_cipher_wasm.js');
  await mod.default();
  wasmMod = mod;
  return wasmMod;
}

function processSync(wasm, msg) {
  const data = new Uint8Array(msg.data);
  const result = wasm.process_rgba_rounds(
    data, msg.width, msg.height,
    msg.method, msg.mode, msg.key,
    msg.blockW, msg.blockH,
    msg.rounds, msg.xor
  );
  return result.buffer;
}

function buildMapSync(wasm, msg) {
  let map;
  if (msg.mapType === 'gilbert_enc') {
    map = wasm.build_gilbert_encrypt_map(msg.width, msg.height, msg.key);
  } else if (msg.mapType === 'gilbert_dec') {
    map = wasm.build_gilbert_decrypt_map(msg.width, msg.height, msg.key);
  } else if (msg.mapType === 'block_enc') {
    map = wasm.build_block_encrypt_map(msg.width, msg.height, msg.blockW, msg.blockH, msg.key);
  } else if (msg.mapType === 'block_dec') {
    map = wasm.build_block_decrypt_map(msg.width, msg.height, msg.blockW, msg.blockH, msg.key);
  }
  return map.buffer;
}

self.onmessage = async function (e) {
  const msg = e.data;
  try {
    const wasm = await ensureWasm();
    let resultBuffer;

    if (msg.type === 'process') {
      resultBuffer = processSync(wasm, msg);
      self.postMessage({ type: 'result', id: msg.id, buffer: resultBuffer }, [resultBuffer]);
    } else if (msg.type === 'buildMap') {
      resultBuffer = buildMapSync(wasm, msg);
      self.postMessage({ type: 'mapResult', id: msg.id, buffer: resultBuffer }, [resultBuffer]);
    }

  } catch (err) {
    self.postMessage({ type: 'error', id: msg.id, message: err.message });
  }
};
