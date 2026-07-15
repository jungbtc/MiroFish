/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 */
import { reactive } from 'vue'
import { DEFAULT_MODEL, DEFAULT_REASONING_EFFORT } from '../constants/llmOptions'

const state = reactive({
  files: [],
  simulationRequirement: '',
  model: DEFAULT_MODEL,
  reasoningEffort: DEFAULT_REASONING_EFFORT,
  isPending: false
})

export function setPendingUpload(
  files,
  requirement,
  modelOrSettings = DEFAULT_MODEL,
  reasoningEffort = DEFAULT_REASONING_EFFORT
) {
  const settings =
    typeof modelOrSettings === 'object' && modelOrSettings !== null
      ? modelOrSettings
      : { model: modelOrSettings, reasoningEffort }

  state.files = files
  state.simulationRequirement = requirement
  state.model = settings.model || settings.llmModel || DEFAULT_MODEL
  state.reasoningEffort =
    settings.reasoningEffort || settings.llmReasoningEffort || DEFAULT_REASONING_EFFORT
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    model: state.model,
    reasoningEffort: state.reasoningEffort,
    llmModel: state.model,
    llmReasoningEffort: state.reasoningEffort,
    isPending: state.isPending
  }
}

export function consumePendingUpload() {
  const pending = getPendingUpload()
  clearPendingUpload()
  return pending
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.model = DEFAULT_MODEL
  state.reasoningEffort = DEFAULT_REASONING_EFFORT
  state.isPending = false
}

export default state
