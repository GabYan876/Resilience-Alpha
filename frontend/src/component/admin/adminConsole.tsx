import { FormEvent, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRecoilValue } from "recoil";
import axios from "axios";
import { baseurl } from "../../recoil/atom";
import { AdminSession, clearAdminSession, loadAdminSession } from "../../session";

// Console du back-office (consigne additionnelle 1) : habilitations, blocages, journal d'accès.
// Le rôle est relu par le back à chaque requête : l'interface masque seulement ce qui serait refusé.

type Habilitation = { identifier: string; role: string };
type Lockout = { identifier: string; locked_until: string };
type Entry = { at: string; event: string; identifier: string; detail: string };

const FIELD =
    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5";
const BUTTON =
    "text-white bg-blue-700 hover:bg-blue-800 disabled:opacity-60 font-medium rounded-lg text-sm px-4 py-2";
const LINK_BUTTON = "text-sm font-medium text-blue-700 hover:underline disabled:opacity-40 disabled:no-underline";
const CARD = "p-5 bg-white border border-gray-200 rounded-lg shadow space-y-4";

// Libellés lisibles des événements `auth.*` (mêmes noms que dans Loki / Grafana).
const EVENT_LABELS: Record<string, string> = {
    "auth.face.recognized": "Visage reconnu",
    "auth.face.rejected": "Visage refusé",
    "auth.face.unavailable": "Caméra ou agent indisponible",
    "auth.password.failed": "Mot de passe incorrect",
    "auth.password.refused_no_face": "Mot de passe sans visage",
    "auth.login.succeeded": "Connexion réussie",
    "auth.access.denied_no_role": "Refus : aucune habilitation",
    "auth.locked": "Identifiant bloqué",
    "auth.locked.refused": "Tentative pendant le blocage",
    "auth.admin.role_granted": "Habilitation accordée",
    "auth.admin.role_revoked": "Habilitation retirée",
    "auth.admin.unlocked": "Identifiant débloqué",
};

const DANGER_EVENTS = new Set([
    "auth.face.rejected",
    "auth.password.failed",
    "auth.locked",
    "auth.locked.refused",
    "auth.access.denied_no_role",
    "auth.face.unavailable",
    "auth.password.refused_no_face",
]);

function time(iso: string): string {
    return new Date(iso).toLocaleTimeString("fr-FR");
}

export default function AdminConsole() {
    const navigate = useNavigate();
    const url = useRecoilValue(baseurl);
    const [session] = useState<AdminSession | null>(loadAdminSession);
    const [habilitations, setHabilitations] = useState<Habilitation[]>([]);
    const [lockouts, setLockouts] = useState<Lockout[]>([]);
    const [journal, setJournal] = useState<Entry[]>([]);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    const isAdmin = session?.role === "admin";
    const headers = { Authorization: "Bearer " + (session?.token ?? "") };

    const logout = useCallback(() => {
        clearAdminSession();
        navigate("/admin");
    }, [navigate]);

    // 401 : jeton expiré ou invalide ; 403 : habilitation retirée entre-temps. Dans les deux cas,
    // retour à la connexion sécurisée.
    const handle = useCallback((err: unknown, fallback: string) => {
        const status = axios.isAxiosError(err) ? err.response?.status : undefined;
        if (status === 401 || (status === 403 && !isAdmin)) {
            logout();
            return;
        }
        const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
        setError(typeof detail === "string" ? detail : fallback);
    }, [isAdmin, logout]);

    const refresh = useCallback(async () => {
        if (!session) return;
        const auth = { headers: { Authorization: "Bearer " + session.token } };
        try {
            const [h, l, j] = await Promise.all([
                axios.get<Habilitation[]>(url + "/auth/admin/habilitations", auth),
                axios.get<Lockout[]>(url + "/auth/admin/lockouts", auth),
                axios.get<Entry[]>(url + "/auth/admin/journal", auth),
            ]);
            setHabilitations(h.data);
            setLockouts(l.data);
            setJournal(j.data);
        } catch (err) {
            handle(err, "Chargement impossible.");
        }
    }, [session, url, handle]);

    useEffect(() => {
        if (!session) {
            navigate("/admin");
            return;
        }
        refresh();
        const timer = setInterval(refresh, 5000); // journal et blocages quasi temps réel
        return () => clearInterval(timer);
    }, [session, navigate, refresh]);

    async function act(path: string, body: object, done: string) {
        setMessage("");
        setError("");
        try {
            await axios.post(url + path, body, { headers });
            setMessage(done);
            await refresh();
        } catch (err) {
            handle(err, "Action refusée.");
        }
    }

    function grant(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const form = e.currentTarget;
        const identifier = (form.elements.namedItem("identifier") as HTMLInputElement).value.trim();
        const role = (form.elements.namedItem("role") as HTMLSelectElement).value;
        act("/auth/admin/habilitations", { identifier, role }, `Habilitation « ${role} » accordée à ${identifier}.`)
            .then(() => form.reset());
    }

    if (!session) return null;

    return (
        <div className="min-h-full bg-gray-100 p-4 sm:p-8">
            <div className="max-w-5xl mx-auto space-y-6">
                <header className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-xl font-medium text-gray-900">Back-office · Resilience-Alpha</h1>
                        <p className="text-sm text-gray-600">
                            {session.name} ({session.identifier}) · rôle{" "}
                            <span className="font-medium">{session.role === "admin" ? "administrateur" : "opérateur (lecture seule)"}</span>
                        </p>
                    </div>
                    <button className={BUTTON} onClick={logout}>Se déconnecter</button>
                </header>

                {message && <p className="text-sm text-green-700" role="status">{message}</p>}
                {error && <p className="text-sm text-red-700" role="alert">{error}</p>}

                <div className="grid gap-6 lg:grid-cols-2">
                    <section className={CARD}>
                        <h2 className="font-medium text-gray-900">Habilitations</h2>
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-gray-500 uppercase">
                                <tr><th className="py-1">Identifiant</th><th>Rôle</th><th></th></tr>
                            </thead>
                            <tbody>
                                {habilitations.map((h) => (
                                    <tr key={h.identifier} className="border-t">
                                        <td className="py-2 break-all">{h.identifier}</td>
                                        <td>{h.role}</td>
                                        <td className="text-right">
                                            {isAdmin && (
                                                <button className={LINK_BUTTON}
                                                    disabled={h.identifier === session.identifier}
                                                    title={h.identifier === session.identifier ? "Impossible de retirer sa propre habilitation" : ""}
                                                    onClick={() => act("/auth/admin/habilitations/revoke", { identifier: h.identifier }, `Habilitation retirée à ${h.identifier}.`)}>
                                                    Retirer
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {isAdmin && (
                            <form className="flex flex-col sm:flex-row gap-2" onSubmit={grant}>
                                <input name="identifier" type="email" required placeholder="identifiant du compte" className={FIELD} />
                                <select name="role" className={FIELD + " sm:w-40"} defaultValue="operator">
                                    <option value="operator">opérateur</option>
                                    <option value="admin">administrateur</option>
                                </select>
                                <button type="submit" className={BUTTON}>Habiliter</button>
                            </form>
                        )}
                    </section>

                    <section className={CARD}>
                        <h2 className="font-medium text-gray-900">Identifiants bloqués</h2>
                        {lockouts.length === 0 ? (
                            <p className="text-sm text-gray-500">Aucun identifiant bloqué.</p>
                        ) : (
                            <ul className="space-y-2">
                                {lockouts.map((l) => (
                                    <li key={l.identifier} className="flex items-center justify-between gap-2 text-sm">
                                        <span className="break-all text-red-700">{l.identifier} · jusqu'à {time(l.locked_until)}</span>
                                        {isAdmin && (
                                            <button className={LINK_BUTTON}
                                                onClick={() => act("/auth/admin/lockouts/unlock", { identifier: l.identifier }, `${l.identifier} débloqué.`)}>
                                                Débloquer
                                            </button>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        )}

                        <h2 className="font-medium text-gray-900 pt-2">Enrôlement des visages</h2>
                        <p className="text-sm text-gray-600">
                            Volontairement hors de cette page : l'enrôlement et la révocation se font sur le PC Hôte,
                            devant la caméra, avec le consentement du membre. Le gabarit chiffré ne transite jamais par le réseau.
                        </p>
                        <pre className="text-xs bg-gray-50 border rounded p-2 overflow-x-auto">
{`python -m app.cli enroll <identifiant>
python -m app.cli revoke <identifiant>`}
                        </pre>
                    </section>
                </div>

                <section className={CARD}>
                    <div className="flex items-center justify-between">
                        <h2 className="font-medium text-gray-900">Journal d'accès</h2>
                        <span className="text-xs text-gray-500">actualisé toutes les 5 s · détail complet dans Grafana</span>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-gray-500 uppercase">
                                <tr><th className="py-1">Heure</th><th>Événement</th><th>Identifiant</th><th>Détail</th></tr>
                            </thead>
                            <tbody>
                                {journal.map((e, i) => (
                                    <tr key={e.at + e.event + i} className="border-t">
                                        <td className="py-2 whitespace-nowrap">{time(e.at)}</td>
                                        <td className={DANGER_EVENTS.has(e.event) ? "text-red-700" : "text-gray-900"}>
                                            {EVENT_LABELS[e.event] ?? e.event}
                                        </td>
                                        <td className="break-all">{e.identifier}</td>
                                        <td className="text-gray-500">{e.detail}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {journal.length === 0 && <p className="text-sm text-gray-500 pt-2">Aucun événement depuis le démarrage du service.</p>}
                    </div>
                </section>
            </div>
        </div>
    );
}
