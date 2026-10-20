import { useEffect, useState } from "react"
import { useRecoilValue } from "recoil";
import { baseurl } from "../../recoil/atom";
import axios from "axios";
import moment from "moment-timezone";

// Montant en centimes -> euros.
function euros(cents: number) {
    return (Number(cents) / 100).toLocaleString("fr-FR", { minimumFractionDigits: 2 });
}

export default function Transaction() {

    const [transc, setTransc]: any = useState([]);
    const url = useRecoilValue(baseurl);

    const f = () => {
        const h = sessionStorage.getItem("token");
        axios.get(url + "/me/transactions", { headers: { Authorization: "Bearer " + h } })
            .then((res) => {
                setTransc(res.data);
            }).catch((err) => {
                console.log(err.response?.data);
            })
    }

    useEffect(f, []);

    return <div className="bg-sky-700 min-h-screen w-full overflow-auto">
        <h1 className="font-semibold text-4xl p-5 pl-10 text-white">Transaction History</h1>
        <div className="flex justify-center w-full">
            {(transc.length === 0) ? <div className="text-center text-2xl text-white pt-10">No Transactions Yet</div> : <TransactionHistory transc={transc} />}
        </div>
    </div>
}

function TransactionHistory(props: any) {

    function when(date: string) {
        return moment(date).tz(moment.tz.guess()).format('YYYY-MM-DD hh:mm:ss A (z)');
    }

    return <div className="bg-white w-full m-2 sm:m-10 rounded-md shadow-md sm:p-5">
        <div className="hidden sm:grid grid-cols-4 gap-4 text-2xl font-semibold border-b-2 border-gray-300">
            <div className="w-fit">Transaction ID</div>
            <div>Sender &amp; Receiver</div>
            <div>Amount</div>
            <div>Date &amp; Time</div>
        </div>
        {props.transc.map((item: any) => {
            const debit = item.direction === "debit";
            return <div key={item.id} className="sm:grid grid-cols-4 gap-4 rounded-sm hover:bg-slate-100 p-5 border-b-2 border-gray-300 w-full">
                <div className="w-fit bg-blue-100 text-blue-800 text-base font-medium me-2 px-2.5 py-0.5 rounded-full dark:bg-blue-900 dark:text-blue-300">
                    <span className="relative sm:hidden">TxID:</span>{item.id}
                </div>
                <div className="flex text-xl items-center">
                    {debit ? "You" : item.counterparty_iban}
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="size-7 ml-2 mr-2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                    </svg>
                    {debit ? item.counterparty_iban : "You"}
                    {item.status !== "settled" && <em className="ml-2 text-slate-400 text-sm">({item.status})</em>}
                </div>
                <div className={(debit ? "text-red-700" : "text-green-700") + " text-xl"}>
                    {debit ? "-" : "+"} € {euros(item.amount_cents)}
                </div>
                <div className="text-xl font-medium">
                    <div className="block sm:hidden">Date &amp; Time-</div>
                    {when(item.created_at)}
                </div>
            </div>
        })}
    </div>
}
