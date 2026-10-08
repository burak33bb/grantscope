import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";
import {
  CONTRACT_ADDRESS,
  EXPLORER_BASE_URL,
  NETWORK_CHAIN_ID,
  NETWORK_LABEL,
} from "./config.js";
import {
  readableWalletError,
  requestAccountPicker,
  revokeAccountPermission,
  switchToStudionet,
} from "./wallet.js";
import "./styles.css";

const readClient = createClient({ chain: studionet });
let writeClient = null;
let walletAddress = "";

const nodes = {
  form: document.querySelector("#review-form"),
  status: document.querySelector("#status-pill"),
  wallet: document.querySelector("#wallet-state"),
  connect: document.querySelector("#connect-wallet"),
  disconnect: document.querySelector("#disconnect-wallet"),
  submit: document.querySelector("#submit-review"),
  read: document.querySelector("#read-latest"),
  result: document.querySelector("#result-label"),
  reason: document.querySelector("#result-reason"),
  score: document.querySelector("#score-value"),
  missing: document.querySelector("#missing-list"),
  txTitle: document.querySelector("#tx-title"),
  txOutput: document.querySelector("#tx-output"),
  txLink: document.querySelector("#tx-link"),
  raw: document.querySelector("#raw-output"),
  network: document.querySelector("#network-label"),
  contractAddress: document.querySelector("#contract-address"),
  contractLink: document.querySelector("#contract-link"),
};

nodes.connect.addEventListener("click", connectWallet);
nodes.disconnect.addEventListener("click", disconnectWallet);
nodes.read.addEventListener("click", readLatest);
nodes.form.addEventListener("submit", submitReview);

initializeUi();

if (window.ethereum) {
  window.ethereum.on?.("accountsChanged", handleAccountsChanged);
  syncExistingWallet();
}

async function connectWallet() {
  try {
    if (!window.ethereum) {
      setTx("wallet missing", "install an eip-1193 wallet.");
      return false;
    }
    await switchToStudionet(window.ethereum);
    if (walletAddress) {
      await revokeAccountPermission(window.ethereum);
    }
    await requestAccountPicker(window.ethereum);
    const [address] = await window.ethereum.request({
      method: "eth_requestAccounts",
    });
    setWallet(address);
    return true;
  } catch (error) {
    setTx("wallet blocked", readableWalletError(error).toLowerCase());
    return false;
  }
}

async function disconnectWallet() {
  if (window.ethereum) {
    try {
      await revokeAccountPermission(window.ethereum);
    } catch {
    }
  }
  walletAddress = "";
  writeClient = null;
  nodes.wallet.textContent = "not connected";
  nodes.connect.textContent = "connect";
  nodes.disconnect.hidden = true;
}

async function submitReview(event) {
  event.preventDefault();
  if (!isReady()) return;
  if (!writeClient) {
    const connected = await connectWallet();
    if (!connected) return;
  }

  try {
    nodes.submit.disabled = true;
    setTx("signing", "confirm review_submission in your wallet.");
    const args = collectArgs();
    const hash = await writeClient.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: "review_submission",
      args,
      value: BigInt(0),
    });
    nodes.txLink.href = `${EXPLORER_BASE_URL}/tx/${hash}`;
    nodes.txLink.hidden = false;
    setTx("submitted", hash);

    const receipt = await readClient.waitForTransactionReceipt({
      hash,
      status: TransactionStatus.FINALIZED,
      fullTransaction: false,
    });
    if (
      receipt.txExecutionResultName &&
      receipt.txExecutionResultName !== ExecutionResult.FINISHED_WITH_RETURN
    ) {
      setTx("execution failed", JSON.stringify(receipt, formatBigInt, 2));
      nodes.status.textContent = "execution failed";
      return;
    }
    setTx("finalized", `transaction finalized.\n${hash}`);
    await wait(1800);
    const report = await readLatest();
    if (!report || Object.keys(report).length === 0) {
      setTx(
        "not stored",
        `transaction finalized, but no report was stored.\ncheck the contract execution in explorer:\n${hash}`,
      );
    }
  } catch (error) {
    setTx("failed", error.message.toLowerCase());
  } finally {
    nodes.submit.disabled = false;
  }
}

async function readLatest() {
  if (!isReady()) return;
  try {
    nodes.status.textContent = "reading";
    const result = await readLatestReport();
    renderReport(result);
    nodes.status.textContent = "contract read";
    return result;
  } catch (error) {
    setTx("read failed", error.message.toLowerCase());
    return {};
  }
}

async function readLatestReport() {
  const latest = normalizeReport(
    await readClient.readContract({
      address: CONTRACT_ADDRESS,
      functionName: "get_latest_report",
      args: [],
      stateStatus: "finalized",
    }),
  );
  if (latest && Object.keys(latest).length > 0) {
    return latest;
  }

  const count = Number(
    await readClient.readContract({
      address: CONTRACT_ADDRESS,
      functionName: "get_report_count",
      args: [],
      stateStatus: "finalized",
    }),
  );
  if (!count) {
    return {};
  }

  return normalizeReport(
    await readClient.readContract({
      address: CONTRACT_ADDRESS,
      functionName: "get_report",
      args: [count],
      stateStatus: "finalized",
    }),
  );
}

function collectArgs() {
  return [
    value("#category"),
    value("#project-name"),
    value("#summary"),
    value("#github-url"),
    value("#contract-url"),
    value("#demo-url"),
    value("#website-url"),
  ];
}

function renderReport(record) {
  nodes.raw.textContent = JSON.stringify(record, formatBigInt, 2);
  if (!record || Object.keys(record).length === 0) {
    nodes.result.textContent = "not reviewed";
    nodes.reason.textContent = "no onchain report yet.";
    nodes.score.textContent = "-";
    nodes.missing.innerHTML = "<li>no report yet</li>";
    return;
  }
  const report = record.report || {};
  nodes.result.textContent = (report.result || "unknown").toLowerCase();
  nodes.reason.textContent = report.reason || "contract returned a report.";
  nodes.score.textContent = String(report.score ?? "-");
  const missing = report.missing?.length ? report.missing : ["none"];
  nodes.missing.replaceChildren(
    ...missing.map((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      return li;
    }),
  );
}

function initializeUi() {
  nodes.network.textContent = `${NETWORK_LABEL.toLowerCase()} ${NETWORK_CHAIN_ID}`;
  if (!CONTRACT_ADDRESS) {
    nodes.status.textContent = "contract pending";
    nodes.submit.disabled = true;
    nodes.read.disabled = true;
    return;
  }
  nodes.status.textContent = "ready";
  nodes.contractAddress.textContent = CONTRACT_ADDRESS;
  nodes.contractLink.href = `${EXPLORER_BASE_URL}/address/${CONTRACT_ADDRESS}`;
  nodes.contractLink.hidden = false;
}

function isReady() {
  if (CONTRACT_ADDRESS) return true;
  setTx("contract pending", "deploy GrantScopeVerifier, then set the address.");
  return false;
}

async function syncExistingWallet() {
  try {
    const accounts = await window.ethereum.request({ method: "eth_accounts" });
    if (accounts.length) {
      setWallet(accounts[0]);
    }
  } catch {
  }
}

function handleAccountsChanged(accounts) {
  if (!accounts.length) {
    disconnectWallet();
    return;
  }
  setWallet(accounts[0]);
}

function setWallet(address) {
  walletAddress = address;
  writeClient = createClient({
    chain: studionet,
    account: walletAddress,
    provider: window.ethereum,
  });
  nodes.wallet.textContent = `${address.slice(0, 6)}...${address.slice(-4)}`;
  nodes.connect.textContent = "change wallet";
  nodes.disconnect.hidden = false;
}

function setTx(title, body) {
  nodes.txTitle.textContent = title;
  nodes.txOutput.textContent = body;
}

function value(selector) {
  return document.querySelector(selector).value.trim();
}

function normalizeReport(result) {
  if (typeof result === "string") {
    try {
      return JSON.parse(result);
    } catch {
      return {};
    }
  }
  return result || {};
}

function formatBigInt(_key, value) {
  return typeof value === "bigint" ? value.toString() : value;
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
