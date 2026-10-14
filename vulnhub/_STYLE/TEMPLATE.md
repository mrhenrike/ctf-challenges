# VulnHub [VM Name]: [Subtitle] — Walkthrough

> **INSTRUÇÃO DE USO:** Preencher todos os campos marcados com [PLACEHOLDER].
> Remover esta instrução antes de publicar.
> NUNCA usar travessão "—" em texto corrido. Usar vírgula, ponto, dois-pontos.

---

**[ABERTURA ESPECÍFICA PARA ESTA VM — nunca genérica]**
Exemplos de openers baseados no estilo do André:
- "Look at guys!! Who would have thought — [algo específico desta VM]!"
- "[Referência ao tema da VM]... and yes, it's another [tipo de desafio]! ( ͡° ͜ʖ ͡°)"
- "Alright guys!! This one has [algo que torna especial]..."
- "Apresento hoje mais um excelente desafio no estilo boot2root CTF. [contexto]"

[Uma frase de agradecimento ao autor da VM, específica ao que torna o desafio especial]

---

| Field | Value |
|-------|-------|
| **Level** | [Easy / Beginner / Intermediate / Hard] |
| **Target VM** | [VM Name + version] |
| **Attacker VM** | Kali Linux [version] |
| **VulnHub** | [https://www.vulnhub.com/entry/...] |
| **Techniques** | [técnica1, técnica2, técnica3 — em ordem cronológica do ataque] |
| **CVEs** | [CVE-XXXX-XXXXX, CVE-XXXX-XXXXX] (se aplicável) |

> **Hints from the author:** (remover esta seção se não houver dicas)
> "[Citação direta das dicas do autor da VM]"

---

## Attack Summary

```
[host-discovery]
    |
    v
[nmap: porta/serviço descoberto]
    |
    v
[técnica de acesso inicial: ex. SQLi / LFI / brute-force]
    |
    v
[acesso inicial: ex. shell como www-data]
    |
    v
[lateral movement: ex. credencial em arquivo -> usuário X]
    |
    v
[escalação de privilégios: técnica]
    |
    v
[ROOT]
    |
    v
[/caminho/para/a/flag]
```

---

## Methodology

1. Host discovery e identificação do alvo na rede
2. Reconhecimento e enumeração de serviços (Nmap)
3. [Técnica específica 1: ex. Enumeração de diretórios web]
4. [Técnica específica 2: ex. Exploração de LFI]
5. [Técnica específica 3: ex. Log poisoning via SMTP]
6. Escalação de privilégios
7. Leitura das flags

---

## Step 1 — Identifying the Target

[Explicação do porquê começamos com host discovery e o que esperamos encontrar]

```bash
route -n
# Identifica a subrede atual: gateway e máscara
```

Scan de hosts ativos na rede:

```bash
# Opção 1: arp-scan (rápido, recomendado para redes locais)
arp-scan --localnet --ignoredups

# Opção 2: nmap ping scan
nmap -sn -T5 192.168.X.0/24
```

[Se necessário atualizar /etc/hosts:]

```bash
echo "[IP]  [hostname]" >> /etc/hosts
cat /etc/hosts
```

OBS.: [Nota relevante sobre este passo específico para esta VM]

---

## Step 2 — Reconnaissance and Vulnerability Enumeration

[Contexto: o que esperamos do Nmap e por que varremos todas as portas]

```bash
nmap -A -T4 -p- [TARGET_IP]
# -A: OS detection, version detection, scripts, traceroute
# -T4: timing agressivo (seguro em lab local)
# -p-: todas as 65535 portas
```

Expected output:

```
[porta]/tcp open  [serviço]  [versão]
[porta]/tcp open  [serviço]  [versão]
```

[Análise do resultado: o que cada serviço aberto significa e onde focaremos]

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery]

---

## Step 3 — [Nome Descritivo da Técnica]

> **O que é [técnica]?** (incluir quando a técnica não é trivialmente conhecida)
> [2-4 frases explicando a vulnerabilidade em linguagem simples]
> [Por que é perigosa? Onde aparece no mundo real?]
> Referência: [link OWASP / Wikipedia / CWE]

[Contexto: por que estamos explorando isso e o que esperamos obter]

```bash
[comando1]
# explicação de flags não óbvias

[comando2]
```

Expected output / resultado:

```
[saída esperada ou representativa]
```

[Narrativa: o que encontramos, o que significa, o que fazer a seguir]

[Alternativas: "you can also use X instead of Y for the same result"]

> **Real-world note:** [Nota relacionando esta técnica a um incidente real, CVE documentado,
> ou caso noticiado. Exemplo: "This same technique was used in the [nome do incidente] breach
> in [ano], where attackers [descrição breve]. Reference: [link de artigo/notícia]"]

> **MITRE ATT&CK:** [TXXxx.xxx Nome da Técnica] [TXXxx.xxx Nome da Sub-técnica]

[Opcional: ASCII emoji no momento de descoberta importante]

---

## Step 4 — [Nome Descritivo]

[Repetir estrutura do Step 3 para cada técnica do ataque]

---

## Step N — Privilege Escalation

[Contexto: como chegamos até aqui e o que precisamos para root]

> **O que é [técnica de privesc]?** (quando aplicável)

```bash
sudo -l
# Verificar permissões sudo do usuário atual

find / -perm -u=s -type f 2>/dev/null
# Buscar por binários SUID
```

[Análise dos resultados: o que cada permissão encontrada significa]

```bash
[exploit command]
```

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [TXXxx Nome da Técnica]

> **GTFOBins reference:** (quando aplicável)
> https://gtfobins.github.io/gtfobins/[binário]/

[Emoji de celebração aqui: `(☞ﾟヮﾟ)☞` ou similar]

---

## Step [N+1] — Root and Flag

**[Emoji de celebração grande] Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/[flag_file]
```

```
[conteúdo da flag ou mensagem de parabéns do autor]
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Flag | `[valor]` | `/caminho/flag.txt` | N/A |
| Hash MD5 | `[hash]` | `[arquivo/serviço]` | `[senha crackeada]` |
| Credential | `[user:pass]` | `[arquivo/serviço]` | SSH/Login |
| Hash NTLM | `[hash]` | `[arquivo]` | `[plaintext]` |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | [vulnerabilidade encontrada] | [como isso aparece em ambientes corporativos] | [lição] |
| 2 | [vulnerabilidade encontrada] | [como isso aparece em ambientes corporativos] | [lição] |
| 3 | [vulnerabilidade encontrada] | [como isso aparece em ambientes corporativos] | [lição] |

**Why does this matter outside the lab?**

[Parágrafo conectando os achados com situações do mundo real. Exemplos de empresas que foram
comprometidas por técnicas similares, referências a breach reports, CVEs famosos associados.]

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | [TA00xx] | [Nome] | [TXXxx] |
| Initial Access | [TA0001] | [Nome] | [TXXxx] |
| Execution | [TA0002] | [Nome] | [TXXxx] |
| Persistence | [TA0003] | [Nome] | [TXXxx] (se aplicável) |
| Privilege Escalation | [TA0004] | [Nome] | [TXXxx] |
| Defense Evasion | [TA0005] | [Nome] | [TXXxx] (se aplicável) |
| Credential Access | [TA0006] | [Nome] | [TXXxx] (se aplicável) |
| Discovery | [TA0007] | [Nome] | [TXXxx] |
| Lateral Movement | [TA0008] | [Nome] | [TXXxx] (se aplicável) |

> ATT&CK Navigator layer for this VM: [link se gerado]
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. [Fix específico para finding 1 - uma frase, ação concreta]
2. [Fix específico para finding 2]
3. [Fix específico para finding 3]

### If You Find Something Similar in Your Environment

**Immediate containment:**
- [Ação imediata 1: isolamento, bloqueio de acesso]
- [Ação imediata 2: rotação de credenciais]
- [Ação imediata 3: revisão de logs]

**MITRE D3FEND countermeasures:**
- [D3-XXX Nome da contramedida] para [técnica atacante T-ID]
- [D3-XXX Nome da contramedida] para [técnica atacante T-ID]

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): [controle relevante]
- Protect (PR): [controle relevante, ex. PR.AC-4: Privileged access management]
- Detect (DE): [controle relevante]
- Respond (RS): [controle relevante]
- Recover (RC): [controle relevante]

**NIST SP 800-53 (Rev. 5) Controls:**
- [AC-6: Least Privilege]
- [SI-10: Information Input Validation]
- [IA-5: Authenticator Management]
- [CM-7: Least Functionality]

**CISA Known Exploited Vulnerabilities:**
- [CVE relevante, se no catálogo CISA KEV]
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: [ASSET / THREAT / RISK / ACCESS / SITUATIONAL AWARENESS / EVENT / SUPPLY CHAIN / WORKFORCE / PROGRAM / TECHNOLOGY]
- Practice: [nome da prática relevante]
- Target MIL: [MIL-1 / MIL-2 / MIL-3]

---

## Final Thoughts

Thanks to [nome do autor da VM] for [algo específico que torna o desafio especial]!

[Parágrafo de reflexão: o que esta VM ensina, por que é relevante além do lab,
como os conceitos se aplicam a ambientes reais ou provas de certificação.]

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: [Medium URL] (when applicable)

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
