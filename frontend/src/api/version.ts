import { apiClient } from './client'

export async function fetchServerVersion(): Promise<string> {
  const { data } = await apiClient.get<{ version: string }>('/version')
  return data.version
}
