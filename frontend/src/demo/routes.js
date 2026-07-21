import { routes as phase12 } from './handlers/phase12.js'
import { routes as phase345 } from './handlers/phase345.js'
import { routes as v2 } from './handlers/v2.js'

// Route entry contract (see src/demo/adapter.js for the full description):
//   {
//     method: 'get' | 'post' | 'delete',
//     pattern: /^\/api\/graph\/task\/(?<taskId>[^/?]+)$/,
//     latency: 'ai' | 'read' | number | [min, max],
//     handler({ params, query, body, config })
//   }
export default [...phase12, ...phase345, ...v2]
