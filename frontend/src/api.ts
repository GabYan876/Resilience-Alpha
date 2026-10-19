// Client HTTP du front. Le jeton vit dans sessionStorage (effacé à la fermeture de l'onglet).

const TOKEN_KEY = "paynow.token";

export type Account = { id: string; iban_fake: string; balance_cents: number; currency: string };
export type HistoryItem = {
  id: string;
  direction: "debit" | "credit";
  counterparty_iban: string;
  amount_cents: number;
  currency: string;
  status: "pending" | "settled" | "failed" | "rejected";
  created_at: string;
};
type AuthResponse = { token: string; resp: { name: string; email: string } };

export class ApiError extends Error {
  constructor(
    public status: number, // 0 = service injoignable (réseau, passerelle)
    message: string,
  ) {
    super(message);
  }
}

export const getToken = (): string | null => sessionStorage.getItem(TOKEN_KEY);
export const logout = (): void => sessionStorage.removeItem(TOKEN_KEY);

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Service injoignable");
  }
  const body = await response.json().catch(() => ({}));
  if (response.ok) return body as T;
  if (response.status === 401 && token) logout(); // jeton expiré : retour à la connexion
  // Un virement refusé par le métier (409) renvoie la transaction, pas un message.
  if (response.status === 409 && body.status === "rejected") {
    throw new ApiError(409, "Virement refusé : solde insuffisant");
  }
  const detail = body.error ?? body.detail;
  throw new ApiError(response.status, typeof detail === "string" ? detail : "Requête refusée");
}

async function authenticate(path: string, payload: object): Promise<AuthResponse> {
  const result = await request<AuthResponse>(path, { method: "POST", body: JSON.stringify(payload) });
  sessionStorage.setItem(TOKEN_KEY, result.token);
  return result;
}

export const login = (email: string, password: string) =>
  authenticate("/auth/login", { email, password });

export const register = (name: string, email: string, number: string, password: string) =>
  authenticate("/auth/register", { name, email, number, password });

export const getAccount = () => request<Account>("/me/account");

export const getHistory = () => request<HistoryItem[]>("/me/transactions");

// `idempotencyKey` : une clé par intention de paiement, pour qu'un double clic ou un
// rejeu après coupure réseau ne débite qu'une fois.
export const transfer = (toAccount: string, amountCents: number, idempotencyKey: string) =>
  request("/me/transfers", {
    method: "POST",
    body: JSON.stringify({
      to_account: toAccount,
      amount_cents: amountCents,
      idempotency_key: idempotencyKey,
    }),
  });
