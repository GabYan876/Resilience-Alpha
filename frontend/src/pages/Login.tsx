import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../api";
import Field from "./Field";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main className="mx-auto mt-24 max-w-sm px-4">
      <h1 className="mb-6 text-2xl font-semibold">Pay Now : connexion</h1>
      <form onSubmit={submit} className="space-y-4">
        <Field label="E-mail" type="email" value={email} onChange={setEmail} />
        <Field label="Mot de passe" type="password" value={password} onChange={setPassword} />
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button className="w-full rounded bg-indigo-600 py-2 text-white hover:bg-indigo-700">
          Se connecter
        </button>
      </form>
      <p className="mt-4 text-sm">
        Pas de compte ? <Link className="text-indigo-600 underline" to="/register">S'inscrire</Link>
      </p>
    </main>
  );
}
