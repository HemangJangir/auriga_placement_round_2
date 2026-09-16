const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: isFormData ? (options.headers || {}) : { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const errorMessage = typeof payload === 'string' ? payload : payload.detail || 'Request failed';
    throw new Error(errorMessage);
  }

  return payload;
}

export const api = {
  getConfig: () => request('/api/config'),
  importPrices: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/api/import-prices', { method: 'POST', body: formData });
  },
  resetPrices: () => request('/api/reset-prices', { method: 'POST' }),
  priceBooking: (payload) => request('/api/price', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
};

export { API_BASE_URL };
