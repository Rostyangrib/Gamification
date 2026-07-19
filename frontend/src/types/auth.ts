export interface User {
  id: number
  email: string
  name: string
  role: string
  department: string
  clearance_level: number
  location: string
  is_active: boolean
  moodle_id?: number | null
}

export interface AuthError {
  detail: string
  reason?: string
}
