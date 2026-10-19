import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Account, ApiError, HistoryItem, getAccount, getHistory, logout, transfer } from "../api";
import { formatCents, parseEuros } from "../money";
import Field from "./Field";

const REFRESH_MS = 3000;

export default function Dashboard() {
  const navigate = useNavigate();
  const [account, setAccount] = useState<Account | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [offline, setOffline] = useState(false);
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  // Une clé par intention de paiement : un double clic ou un rejeu ne débite qu'une fois.
  const idempotencyKey = useRef(crypto.randomUUID());

  const refresh = useCallback(async () => {
    try {
      const [acc, items] = await Promise.all([getAccount(), getHistory()]);
      setAccount(acc);
      setHistory(items);
      setOffline(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) navigate("/login");
      else setOffline(true); // l'incident reste visible, la reprise aussi : on réessaie
    }
  }, [navigate]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cents = parseEuros(amount);
    if (cents === null) return setMessage({ ok: false, text: "Montant invalide (ex. 12,50)" });
    try {
      await transfer(to.trim(), cents, idempotencyKey.current);
      idempotencyKey.current = crypto.randomUUID();
      setMessage({ ok: true, text: `Virement de ${formatCents(cents)} effectué` });
      setTo("");
      setAmount("");
      void refresh();
    } catch (e) {
      setMessage({ ok: false, text: (e as Error).message });
    }
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-4 py-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pay Now</h1>
        <button
          className="text-sm text-slate-600 underline"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Se déconnecter
        </button>
      </header>

      {offline && (
        <p role="status" className="rounded bg-amber-100 px-3 py-2 text-sm text-amber-900">
          Service momentanément indisponible, nouvelle tentative automatique…
        </p>
      )}

      <section className="rounded bg-white p-4 shadow">
        <p className="text-sm text-slate-500">Solde</p>
        <p className="text-3xl font-semibold">{account ? formatCents(account.balance_cents) : "…"}</p>
        {account && <p className="text-xs text-slate-500">{account.iban_fake}</p>}
      </section>

      <section className="rounded bg-white p-4 shadow">
        <h2 className="mb-3 font-medium">Envoyer de l'argent</h2>
        <form onSubmit={submit} className="space-y-3">
          <Field label="IBAN du bénéficiaire" value={to} onChange={setTo} />
          <Field label="Montant (€)" value={amount} onChange={setAmount} />
          {message && (
            <p role="alert" className={message.ok ? "text-sm text-green-700" : "text-sm text-red-600"}>
              {message.text}
            </p>
          )}
          <button className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700">
            Envoyer
          </button>
        </form>
      </section>

      <section className="rounded bg-white p-4 shadow">
        <h2 className="mb-3 font-medium">Historique</h2>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">Aucune opération.</p>
        ) : (
          <ul className="divide-y text-sm">
            {history.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-2">
                <span>
                  {item.direction === "debit" ? "Vers" : "De"} {item.counterparty_iban}
                  {item.status !== "settled" && (
                    <em className="ml-2 text-slate-500">({item.status})</em>
                  )}
                </span>
                <span
                  className={item.direction === "debit" ? "text-red-600" : "text-green-700"}
                >
                  {item.direction === "debit" ? "-" : "+"}
                  {formatCents(item.amount_cents)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
