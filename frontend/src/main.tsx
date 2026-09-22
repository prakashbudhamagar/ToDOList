import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './tailwind.css'
import './main.scss'
import App from './App'

const container = document.getElementById('root')
if (!container) {
  throw new Error('index.html must contain a #root element.')
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
