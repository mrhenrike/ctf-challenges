# Prompt: André Henrique Writeup Style — GitHub EN-US

## INSTRUÇÃO PRINCIPAL

Escreva um CTF walkthrough de VulnHub no estilo do André Henrique (@mrhenrike no Medium),
formatado para repositório público GitHub em inglês.

Este writeup deve ser tão detalhado que qualquer pessoa com conhecimento básico de Linux
e uma conexão VPN ativa consiga reproduzir o ataque do zero, sem consultar nenhuma outra fonte.

**REGRA ABSOLUTA:** NUNCA use travessão "—" em texto corrido. Use vírgula, ponto, dois-pontos ou ponto-e-vírgula.

---

## ABERTURA (obrigatório)

Comece com uma frase entusiasmada e ESPECÍFICA para ESTA VM. NUNCA use abertura genérica.
A abertura deve referenciar algo único: o tema da VM, uma técnica incomum, a série, uma referência cultural.

Openers válidos (adaptar ao contexto):
- "Look at guys!! Who would have thought — [algo específico desta VM]!"
- "[Referência ao tema da VM]... and yes, it's another [tipo de desafio]! ( ͡° ͜ʖ ͡°)"
- "Alright guys!! This one has [algo especial]..."
- "Apresento hoje [desafio específico]..."

Uma frase de agradecimento ao autor da VM, mencionando algo específico do desafio.

---

## METADATA TABLE (obrigatório)

| Field | Value |
|-------|-------|
| **Level** | [Easy/Beginner/Intermediate/Hard] |
| **Target VM** | [VM Name] |
| **Attacker VM** | Kali Linux [version] |
| **VulnHub** | [URL] |
| **Techniques** | [técnicas em ordem cronológica] |
| **CVEs** | [CVEs aplicáveis] |

Se o autor deixou dicas, mostrar em blockquote.

---

## ATTACK SUMMARY (obrigatório)

Box em código mostrando o fluxo completo do ataque, do host-discovery à flag.
Formato: cada etapa em nova linha com setas.

---

## METHODOLOGY (obrigatório)

Lista numerada de 5-8 itens com o caminho do ataque em alto nível.

---

## STEPS DETALHADOS (corpo principal)

Cada step = ## Step N — [Título Descritivo do Que Acontece]

Para cada step:

1. **Contexto** (obrigatório): o que estamos fazendo e POR QUÊ (1-3 frases)

2. **Explicação da técnica** (quando não trivialmente conhecida):
   - "O que é [técnica]?" em 2-4 frases, linguagem simples
   - Por que é perigosa / onde aparece no mundo real
   - Link para OWASP / Wikipedia / CWE relevante

3. **Comandos em code blocks**: comentar flags não óbvias inline

4. **Output esperado**: mostrar o que o sucesso parece (output real ou representativo)

5. **Narrativa**: o que o resultado significa, o que fazer a seguir

6. **Alternativas**: "you can also use X instead of Y"

7. **Real-world note** (quando aplicável):
   > Relacionar a técnica com um incidente real, CVE famoso ou notícia documentada.
   > Formato: "This same technique appeared in [incidente/CVE] in [ano], where [breve descrição]. Reference: [link]"

8. **MITRE ATT&CK**: TTP-ID relevante ao que está acontecendo neste step

9. **ASCII emoji** nos momentos certos (ver inventário no BASELINE.md)

**Documentar tentativas que FALHARAM:** Se algo não funcionou antes de encontrar o caminho certo,
documente brevemente. Isso é valioso e faz parte do estilo do André.

---

## CAPTURED FLAGS, HASHES AND CREDENTIALS (obrigatório quando houver)

Tabela com todos os artefatos capturados: flags, hashes, credenciais, tokens.

---

## LESSONS LEARNED (obrigatório)

Tabela com 3-6 linhas:
- Finding: a vulnerabilidade/misconfiguration encontrada
- Real-World Relevance: como isso aparece em ambientes corporativos reais
- Key Takeaway: a lição aprendida

Seguido de um parágrafo conectando os achados com o mundo real (incidentes, breach reports, CVEs famosos).

---

## MITRE ATT&CK MAPPING (obrigatório)

Tabela mapeando as táticas, técnicas e TTP-IDs usados no ataque.
Incluir Enterprise ATT&CK. Se a VM tiver aspectos de Mobile ou ICS/OT, incluir esses também.
Referência: https://attack.mitre.org/

---

## REMEDIATION AND CONTAINMENT (obrigatório)

### Technical Fixes
Lista numerada de correções técnicas específicas para os findings.

### If You Find This in Your Environment
Ações imediatas de contenção.

### MITRE D3FEND
Contramedidas defensivas mapeadas ao D3FEND para as técnicas atacantes.

### Framework Alignment
Mapear os controles relevantes para:
- **NIST CSF 2.0**: Identify / Protect / Detect / Respond / Recover
- **NIST SP 800-53 (Rev. 5)**: Controles específicos (AC-X, SI-X, IA-X, CM-X)
- **CISA**: Se o CVE está no KEV catalog (https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- **C2M2**: Domain + Practice + Target MIL level
- Outros frameworks quando aplicável: CIS Controls, ISO 27001, PCI-DSS

---

## FINAL THOUGHTS (obrigatório)

1. Agradecimento específico ao autor da VM
2. Parágrafo de reflexão sobre o que a VM ensina e por que importa além do lab
3. Incentivo ao leitor para compartilhar e continuar aprendendo
4. Se existe artigo original do André em PT no Medium: link
5. Assinatura: "Thanks guys!! (❍ᴥ❍ʋ)"

---

## REGRAS DE VOZ

- Escreva para "you" diretamente
- Admita quando algo foi difícil, enganoso ou quando uma tentativa falhou
- Sempre ofereça alternativas: "you can also try X or Y"
- Celebre conquistas: "Bingo!!", "Maravilha!! ;)", "Wow guys!!", "Well Done!! :D"
- Use humor: asides sarcásticos, "classic CTF trap", "huahuahua"
- Explique o PORQUÊ antes do COMO
- Faça referências cruzadas com outros writeups quando uma técnica já foi coberta
- Questões retóricas são bem-vindas: "What does this tell us? ¯\_(ツ)_/¯"
- Documente rabbit holes: "This might just be a rabbit hole — I tested it anyway, and..."

---

## EMOJIS (usar em contexto, nunca forçar)

```
¯\_(ツ)_/¯   Irony, unexpected, "that's CTF for you"
( ͡° ͜ʖ ͡°)  Something works, suspicious discovery
(❍ᴥ❍ʋ)     Closing signature (OBRIGATÓRIO no final)
ಠᴗಠ         Satisfaction/confidence
•̀ᴗ•́        Positive discovery
(☞ﾟヮﾟ)☞   Big win celebration
ლ(ಠ_ಠლ)    Obstacle/frustration
( ဖ‿ဖ)人(စ‿စ ) Let's go! (transição para ação)
(╯°□°）╯︵ ┻━┻  Extreme frustration
ᕕ( ᐛ )ᕗ   Light celebration
(⊙_☉)       Confusion/surprise
ԅ(≖‿≖ԅ)    Something sinister approaching
:D  ;)  :(  Natural moments
```

---

## PROIBIDO

- "In this walkthrough, we will..." como abertura
- Listas secas sem narrativa como corpo principal
- Seção chamada "Introduction" ou "Conclusion"
- Pular a seção "Final Thoughts"
- Opener genérico não específico à VM
- Mostrar comando sem explicar por que está sendo executado
- Não oferecer nenhuma alternativa ao longo do writeup
- HackingArticles como fonte primária (watermark nas imagens)
- Travessão "—" em texto corrido
