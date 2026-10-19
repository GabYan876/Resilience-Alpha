// L'argent reste en centimes entiers : aucun flottant ne touche un montant.

export function formatCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const euros = Math.floor(abs / 100).toLocaleString("fr-FR");
  return `${sign}${euros},${String(abs % 100).padStart(2, "0")} €`;
}

// "12", "12,5" ou "12.50" -> 1250 ; toute autre saisie (ou zéro) -> null.
export function parseEuros(input: string): number | null {
  const match = /^(\d{1,9})(?:[.,](\d{1,2}))?$/.exec(input.trim());
  if (!match) return null;
  const cents = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  return cents > 0 ? cents : null;
}
