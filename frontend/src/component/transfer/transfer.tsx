import { FormEvent, useEffect, useRef, useState } from "react";
import { useRecoilValue, useSetRecoilState } from "recoil";
import axios from "axios";
import uid from "../../assets/uid.svg";
import { baseurl, navatom, userinfo } from "../../recoil/atom";

// Le back ne fait que le virement par IBAN (pas d'UID/e-mail/numéro, pas de PIN,
// pas de demande). Ce formulaire appelle directement /me/transfers.
export default function Transfer() {

    const set = useSetRecoilState(navatom);
    useEffect(() => { set(4); }, [set]);

    const url = useRecoilValue(baseurl);
    const user: any = useRecoilValue(userinfo);
    const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
    // Une clé par intention de paiement : un double clic ne débite qu'une fois.
    const idemKey = useRef(crypto.randomUUID());

    function send(form: FormEvent<HTMLFormElement>) {
        form.preventDefault();
        setMessage(null);
        const el = form.currentTarget;
        const receiver = (el.receiver.value as string).trim();
        const amount = (el.amount.value as string).trim();
        const m = /^(\d{1,9})(?:[.,](\d{1,2}))?$/.exec(amount);
        if (!m) return setMessage({ ok: false, text: "Montant invalide (ex. 12,50)" });
        const cents = Number(m[1]) * 100 + Number((m[2] ?? "").padEnd(2, "0"));
        if (cents <= 0) return setMessage({ ok: false, text: "Montant invalide" });

        const h = sessionStorage.getItem("token");
        axios.post(url + "/me/transfers",
            { to_account: receiver, amount_cents: cents, idempotency_key: idemKey.current },
            { headers: { Authorization: "Bearer " + h } })
            .then(() => {
                idemKey.current = crypto.randomUUID();
                setMessage({ ok: true, text: "Virement effectué ✅" });
                el.reset();
            }).catch((err) => {
                const d = err.response?.data;
                const txt = (err.response?.status === 409) ? "Virement refusé : solde insuffisant"
                    : (typeof d?.error === "string" && d.error) || (typeof d?.detail === "string" && d.detail) || (Array.isArray(d?.detail) && d.detail[0]?.msg) || "Virement refusé";
                setMessage({ ok: false, text: txt });
            });
    }

    return <div className="pl-2 pr-2 sm:pl-14 sm:pr-14 pb-1 pt-8 bg-sky-700 min-h-screen">
        <div className="font-bold text-white text-4xl mb-6">Transfer</div>

        <div className="pt-8 h-full w-full bg-white rounded-lg shadow-md">
            <form onSubmit={send}>
                <div className="flex flex-col sm:flex-row">
                    <div className="sm:w-1/3 flex flex-col items-center justify-center">
                        <div className="font-bold text-5xl sm:text-6xl">
                            € {(Number(user.balance) / 100).toLocaleString("fr-FR", { minimumFractionDigits: 2 })}
                        </div>
                        <div className="m-5 bg-blue-100 text-blue-800 text-2xl font-medium px-2.5 py-0.5 rounded">Account Balance</div>
                        <div className="flex items-center text-slate-500">
                            <img src={uid} alt="" width={24} />
                            <span className="ml-2 font-mono">{user.uid}</span>
                        </div>
                    </div>

                    <div className="sm:w-2/3">
                        <div className="sm:m-16 m-5">
                            <label className="block mb-6 text-2xl font-medium text-gray-900">IBAN du bénéficiaire</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 start-0 flex items-center ps-3.5 pointer-events-none">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="size-6">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                                    </svg>
                                </div>
                                <input type="text" name="receiver" placeholder="ex. FR-TEST-0002" required
                                    className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full ps-10 p-2.5" />
                            </div>
                        </div>
                        <div className="sm:m-16 m-5">
                            <label className="block mb-6 text-2xl font-medium text-gray-900">Montant (€)</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 start-0 flex items-center ps-3.5 pointer-events-none">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="size-6">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 8.25H9m6 3H9m3 6-3-3h1.5a3 3 0 1 0 0-6M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                                    </svg>
                                </div>
                                <input type="text" name="amount" placeholder="12,50" required
                                    className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full ps-10 p-2.5" />
                            </div>
                        </div>
                        <div className="flex flex-col items-center justify-center pb-8">
                            {message && (
                                <div className={(message.ok ? "text-green-700" : "text-red-600") + " mb-2 font-medium"}>{message.text}</div>
                            )}
                            <button type="submit"
                                className="text-white bg-green-700 hover:bg-green-800 focus:outline-none focus:ring-4 focus:ring-green-300 font-medium rounded-full text-2xl px-8 py-2.5 text-center">
                                Send
                            </button>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    </div>
}
