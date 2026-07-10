/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  llmModel: 'gpt-5.4-mini',
  llmReasoningEffort: 'low',
  isPending: false
})

export function setPendingUpload(files, requirement, settings = {}) {
  state.files = files
  state.simulationRequirement = requirement
  state.llmModel = settings.llmModel || 'gpt-5.4-mini'
  state.llmReasoningEffort = settings.llmReasoningEffort || 'low'
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    llmModel: state.llmModel,
    llmReasoningEffort: state.llmReasoningEffort,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.llmModel = 'gpt-5.4-mini'
  state.llmReasoningEffort = 'low'
  state.isPending = false
}

export default state
