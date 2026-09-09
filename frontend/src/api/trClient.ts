const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.json();
}

export const trApi = {
  data: {
    modalidades: () => get<Record<string, unknown>[]>('/tr/data/modalidades'),
    diretorias: () => get<Record<string, unknown>[]>('/tr/data/diretorias'),
    perfis: () => get<Record<string, unknown>>('/tr/data/perfis'),
    norma: () => get<Record<string, unknown>>('/tr/data/norma'),
    objetos: () => get<Record<string, unknown>[]>('/tr/data/objetos'),
    criterios: () => get<Record<string, unknown>[]>('/tr/data/criterios'),
  },
  compose: {
    perfil: (modalidade: string, funcoes: string[], temas: string[], experiencia = '', enfases: string[] = [], recortes: string[] = []) =>
      post<{ text: string }>('/tr/compose/perfil', { modalidade, funcoes, temas, experiencia, enfases, recortes }),
    atividades: (funcoes: string[], temas: string[]) =>
      post<{ text: string }>('/tr/compose/atividades', { funcoes, temas }),
    criterios: (modalidade: string, funcoes: string[], provaPratica = false) =>
      post<{ text: string }>('/tr/compose/criterios', { modalidade, funcoes, prova_pratica: provaPratica }),
    objeto: (projetoNome: string) =>
      post<{ text: string }>('/tr/compose/objeto', { projetoNome }),
  },
  generate: (form: Record<string, unknown>, docType = 'tr') =>
    post<{ sections: Record<string, string>; text: string }>('/tr/generate', { type: docType, form }),
  validate: (form: Record<string, unknown>) =>
    post<{ checks: Record<string, unknown>[]; summary: string }>('/tr/validate', { form }),
  diffDias: (a: string, b: string) =>
    post<{ dias: number | null }>('/tr/diff-dias', { a, b }),
};
