import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRecoilValue, useSetRecoilState } from "recoil";
import axios from "axios";
import { baseurl, logined, userinfo } from "../../recoil/atom";
import { saveSession, toUser } from "../../session";

// Connexion du back-office (consigne additionnelle 1) :
// identifiant -> reconnaissance du visage (caméra du PC Hôte) -> mot de passe.
type Step = "identifier" | "face" | "password" | "locked";

const FIELD =
    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5";
const BUTTON =
    "w-full text-white bg-blue-700 hover:bg-blue-800 disabled:opacity-60 font-medium rounded-lg text-sm px-5 py-2.5";

// Traduit une erreur HTTP du back en message affichable ; 423 est traité à part (compte à rebours).
function messageFor(status: number | undefined, fallback: string): string {
    switch (status) {
        case 401: return "Mot de passe incorrect.";
        case 403: return "Visage non reconnu. Accès refusé.";
        case 503: return "Vérification du visage indisponible : l'accès reste fermé.";
        default: return fallback;
    }
}

export default function AdminLogin() {
    const navigate = useNavigate();
    const url = useRecoilValue(baseurl);
    const setUser = useSetRecoilState(userinfo);
    const setLogined = useSetRecoilState(logined);

    const [step, setStep] = useState<Step>("identifier");
    const [identifier, setIdentifier] = useState("");
    const [message, setMessage] = useState("");
    const [remaining, setRemaining] = useState(0);

    // Compte à rebours du blocage ; à zéro, on repart de l'identifiant.
    useEffect(() => {
        if (step !== "locked") return;
        if (remaining <= 0) {
            setStep("identifier");
            setMessage("");
            return;
        }
        const timer = setTimeout(() => setRemaining((s) => s - 1), 1000);
        return () => clearTimeout(timer);
    }, [step, remaining]);

    function fail(err: unknown, fallback: string): number | undefined {
        const status = axios.isAxiosError(err) ? err.response?.status : undefined;
        if (status === 423 && axios.isAxiosError(err)) {
            const retry = Number(err.response?.headers["retry-after"]);
            setRemaining(Number.isFinite(retry) && retry > 0 ? retry : 300);
            setStep("locked");
            setMessage("Trop de tentatives : compte bloqué.");
        } else {
            setMessage(messageFor(status, fallback));
        }
        return status;
    }

    async function identify(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setMessage("");
        setStep("face");
        try {
            await axios.post(url + "/auth/admin/identify", { identifier });
            setStep("password");
        } catch (err) {
            if (fail(err, "Connexion échouée") !== 423) setStep("identifier");
        }
    }

    async function login(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setMessage("");
        const password = (e.currentTarget.elements.namedItem("password") as HTMLInputElement).value;
        try {
            const res = await axios.post(url + "/auth/admin/login", { identifier, password });
            saveSession(res.data.token, res.data.resp);
            setUser(toUser(res.data.resp));
            setLogined(true);
            navigate("/home");
        } catch (err) {
            // 403 : le visage n'est plus validé, il faut recommencer depuis l'identifiant.
            if (fail(err, "Connexion échouée") === 403) setStep("identifier");
        }
    }

    return (
        <div className="h-full flex items-center justify-center bg-gray-100 p-4">
            <div className="w-full max-w-md p-6 bg-white border border-gray-200 rounded-lg shadow space-y-6">
                <h1 className="text-xl font-medium text-gray-900">Back-office · connexion sécurisée</h1>

                {step === "identifier" && (
                    <form className="space-y-4" onSubmit={identify}>
                        <label htmlFor="identifier" className="block text-sm font-medium text-gray-900">
                            Identifiant
                        </label>
                        <input id="identifier" type="email" className={FIELD} required autoFocus
                            value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
                        <button type="submit" className={BUTTON}>Continuer</button>
                    </form>
                )}

                {step === "face" && (
                    <div className="space-y-2 text-center" role="status">
                        <p className="text-sm text-gray-900">Regardez la caméra du poste…</p>
                        <p className="text-xs text-gray-500">Vérification du visage en cours.</p>
                    </div>
                )}

                {step === "password" && (
                    <form className="space-y-4" onSubmit={login}>
                        <p className="text-sm text-green-700">Visage reconnu pour {identifier}.</p>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-900">
                            Mot de passe
                        </label>
                        <input id="password" name="password" type="password" className={FIELD} required autoFocus />
                        <button type="submit" className={BUTTON}>Se connecter</button>
                    </form>
                )}

                {step === "locked" && (
                    <p className="text-sm text-red-700" role="alert">
                        Compte bloqué. Nouvel essai possible dans {Math.floor(remaining / 60)} min{" "}
                        {String(remaining % 60).padStart(2, "0")} s.
                    </p>
                )}

                {message && step !== "locked" && (
                    <p className="text-sm text-red-700" role="alert">{message}</p>
                )}
            </div>
        </div>
    );
}
