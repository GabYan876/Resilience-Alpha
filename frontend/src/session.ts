// Session du navigateur : jeton et profil gardés en sessionStorage pour survivre à un
// rafraîchissement de page (effacés à la fermeture de l'onglet ou à la déconnexion).
// Le profil est fictif et sans secret ; le solde est relu auprès du back à chaque ouverture.

const TOKEN = "token";
const PROFILE = "profile";

// Profil renvoyé par /auth/* : { _id, name, email, number, iban, balance_cents }.
// L'UI d'origine attend `uid` (IBAN) et `balance` (centimes).
export function toUser(r: { iban: string; balance_cents: number }) {
    return { ...r, uid: r.iban, balance: r.balance_cents };
}

export function saveSession(token: string, resp: { iban: string; balance_cents: number }) {
    try {
        sessionStorage.setItem(TOKEN, token);
        sessionStorage.setItem(PROFILE, JSON.stringify(toUser(resp)));
    } catch { /* stockage indisponible : la session reste en mémoire */ }
}

export function loadSession(): { token: string | null; user: Record<string, unknown> } {
    try {
        const token = sessionStorage.getItem(TOKEN);
        const raw = sessionStorage.getItem(PROFILE);
        if (token && raw) return { token, user: JSON.parse(raw) };
    } catch { /* stockage illisible : on repart déconnecté */ }
    return { token: null, user: {} };
}

export function clearSession() {
    try {
        sessionStorage.removeItem(TOKEN);
        sessionStorage.removeItem(PROFILE);
    } catch { /* rien à effacer */ }
}

// Session du back-office : jeton distinct (audience « backoffice »), refusé par l'API client.
// Durée courte côté serveur (15 min) ; effacée à la déconnexion ou à la fermeture de l'onglet.
const ADMIN = "adminSession";

export type AdminSession = { token: string; identifier: string; name: string; role: "admin" | "operator" };

export function saveAdminSession(session: AdminSession) {
    try {
        sessionStorage.setItem(ADMIN, JSON.stringify(session));
    } catch { /* stockage indisponible : la console redemandera la connexion */ }
}

export function loadAdminSession(): AdminSession | null {
    try {
        const raw = sessionStorage.getItem(ADMIN);
        return raw ? (JSON.parse(raw) as AdminSession) : null;
    } catch {
        return null;
    }
}

export function clearAdminSession() {
    try {
        sessionStorage.removeItem(ADMIN);
    } catch { /* rien à effacer */ }
}
