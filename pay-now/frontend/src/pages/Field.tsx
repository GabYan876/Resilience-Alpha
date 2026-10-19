type Props = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  hint?: string;
};

export default function Field({ label, value, onChange, type = "text", hint }: Props) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        className="w-full rounded border border-slate-300 px-3 py-2"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
      />
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
    </label>
  );
}
