// Les demandes de paiement ne sont pas prises en charge par le back actuel :
// ce panneau est purement informatif (aucun appel API).
export default function Rightcomp() {
    return <div className="m-4 p-4 bg-white rounded-xl shadow-lg sm:w-1/3 h-auto">
        <div>
            <span className=" bg-indigo-100 text-indigo-800 text-2xl font-medium me-2 px-2.5 py-0.5 rounded-full dark:bg-indigo-900 dark:text-indigo-300">Pending Request</span>
        </div>
        <div className="pt-10 flex flex-col items-center justify-center text-center text-2xl font-bold text-gray-500">
            No Payment Request
        </div>
    </div>
}
