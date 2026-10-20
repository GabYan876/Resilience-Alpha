// Liste de blocage de sources, alimentée par le moteur de remédiation.
//
// Fichier partagé en lecture seule avec le WAF, une entrée par ligne :
//   ip:<adresse>   source réseau vue par le WAF
//   sub:<id>       sujet (`sub`) du jeton JWT présenté dans Authorization
// Le sujet existe parce que, sous Docker Desktop, le WAF voit l'IP de la passerelle Docker
// et non celle de l'attaquant : l'IP seule ne distingue personne (voir docs/architecture).
// La signature du jeton n'est pas vérifiée ici : l'API le fait, et une revendication
// falsifiée ne peut qu'être bloquée, jamais autorisée.
import fs from 'fs';

const BLOCKLIST = '/blocklist/blocked.txt';

function subject(r) {
  const auth = r.headersIn['Authorization'];
  if (!auth || auth.slice(0, 7) !== 'Bearer ') return '';
  try {
    const payload = auth.slice(7).split('.')[1];
    return String(JSON.parse(Buffer.from(payload, 'base64url').toString()).sub || '');
  } catch (e) {
    return '';
  }
}

function blocked(r) {
  let text;
  try {
    text = fs.readFileSync(BLOCKLIST, 'utf8');
  } catch (e) {
    return '0'; // pas de liste = personne de bloqué
  }
  const entries = text.split('\n').map((l) => l.trim());
  const sub = subject(r);
  if (sub && entries.indexOf('sub:' + sub) !== -1) return '1';
  return entries.indexOf('ip:' + r.remoteAddress) !== -1 ? '1' : '0';
}

export default { blocked };
