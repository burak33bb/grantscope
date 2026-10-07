import assert from "node:assert/strict";
import {
  requestAccountPicker,
  revokeAccountPermission,
  STUDIONET,
  switchToStudionet,
} from "../src/wallet.js";

const switchCalls = [];
await switchToStudionet({
  request: async (payload) => {
    switchCalls.push(payload);
  },
});

assert.deepEqual(switchCalls, [
  {
    method: "wallet_switchEthereumChain",
    params: [{ chainId: STUDIONET.chainId }],
  },
]);

const addCalls = [];
await switchToStudionet({
  request: async (payload) => {
    addCalls.push(payload);
    if (payload.method === "wallet_switchEthereumChain") {
      const error = new Error("unknown chain");
      error.code = 4902;
      throw error;
    }
  },
});

assert.deepEqual(addCalls, [
  {
    method: "wallet_switchEthereumChain",
    params: [{ chainId: STUDIONET.chainId }],
  },
  {
    method: "wallet_addEthereumChain",
    params: [STUDIONET],
  },
]);

const pickerCalls = [];
await requestAccountPicker({
  request: async (payload) => {
    pickerCalls.push(payload);
  },
});

assert.equal(pickerCalls[0].method, "wallet_requestPermissions");

const revokeCalls = [];
await revokeAccountPermission({
  request: async (payload) => {
    revokeCalls.push(payload);
  },
});

assert.equal(revokeCalls[0].method, "wallet_revokePermissions");

console.log("wallet flow ok");
