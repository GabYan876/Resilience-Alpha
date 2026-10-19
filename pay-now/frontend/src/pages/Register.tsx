import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api";
import Field from "./Field";

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [number, setNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await register(name, email, number, password);
      navigate("/");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main className="mx-auto mt-16 max-w-sm px-4">
      <h1 className="mb-6 text-2xl font-semibold">Pay Now : inscription</h1>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nom complet" value={name} onChange={setName} />
        <Field label="E-mail" type="email" value={email} onChange={setEmail} />
        <Field label="Téléphone" type="tel" value={number} onChange={setNumber} hint="10 à 15 chiffres" />
        <Field
          label="Mot de passe"
          type="password"
          value={password}
          onChange={setPassword}
          hint="8 caractères minimum"
        />
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button className="w-full rounded bg-indigo-600 py-2 text-white hover:bg-indigo-700">
          Créer mon compte
        </button>
      </form>
      <p className="mt-4 text-sm">
        Déjà inscrit ? <Link className="text-indigo-600 underline" to="/login">Se connecter</Link>
      </p>
    </main>
  );
}
