(function () {
  'use strict';

  const state = window.KaguyaState || (window.KaguyaState = {});

  function begin(controller) {
    state.currentAgentAbortController = controller || null;
    state.currentAgentRunId = null;
    state.agentRunning = true;
  }

  function observeFrame(frame) {
    if (!frame || typeof frame !== 'object') return;
    if (frame.run_id) {
      state.currentAgentRunId = frame.run_id;
    }
    if (frame.type === 'run_started' && frame.run_id) {
      state.currentAgentRunId = frame.run_id;
    }
    if (frame.type === 'aborted' || frame.done || frame.type === 'done') {
      state.agentRunning = false;
    }
  }

  function finish() {
    state.agentRunning = false;
    state.currentAgentAbortController = null;
    state.currentAgentRunId = null;
  }

  async function stop() {
    const runId = state.currentAgentRunId || null;
    const controller = state.currentAgentAbortController || null;
    if (controller) {
      try {
        controller.abort();
      } catch (_) {}
    }
    state.currentAgentAbortController = null;
    if (!runId) {
      state.agentRunning = false;
      return { success: false, aborted: false, error: 'missing_run_id', message: '当前无活动 Agent 任务' };
    }
    const result = window.KaguyaAPI && window.KaguyaAPI.abortAgent
      ? await window.KaguyaAPI.abortAgent(runId)
      : await fetch('/agent/abort', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_id: runId }),
        }).then(function (r) { return r.json(); });
    if (result && result.aborted !== false) {
      state.currentAgentRunId = null;
      state.agentRunning = false;
    }
    return result;
  }

  window.KaguyaAgent = {
    begin,
    observeFrame,
    finish,
    stop,
  };
})();
