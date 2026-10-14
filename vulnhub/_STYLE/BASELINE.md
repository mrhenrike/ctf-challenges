# André Henrique — CTF Writeup Style Baseline v2.0
## Análise Completa de 10 Artigos + Benchmark Best-of-Three + Framework Integration

> Corpus: 10 artigos do Medium @mrhenrike analisados
> (symfonos-1, dc-6, jigsaw-1, mission-pumpkin-1/2/3, zeus-1, matrix-v3, unknown-device-1/2)
> Data: 2026-10-14

---

## PARTE 1 — ANATOMIA DO ARTIGO

```
[ABERTURA ENTUSIASMADA E ESPECÍFICA À VM]
    |
    v
[APRESENTAÇÃO DA VM]
   Autor, contexto da série (quando série), link VulnHub
    |
    v
[METADADOS]
   Level / VM Alvo / VM Atacante
   "O que sabemos?" (dicas do autor + flags esperadas, se houver)
    |
    v
"So... Let's go guys!! ( ဖ‿ဖ)人(စ‿စ )"  [quando VM é mais desafiadora]
    |
    v
[SEÇÃO: Configuração do Lab]  [apenas quando VM tem rede estática ou setup especial]
    |
    v
[SEÇÃO: Identificando o Alvo]  — host discovery
    |
    v
[SEÇÃO: Reconhecimento / Enumeração de Vulnerabilidades]  — nmap + análise
    |
    v
[SEÇÕES TÉCNICAS — uma por técnica/vetor]
   Cada seção tem nome descritivo: "Explorando LFI via Plugin Mail Masta"
    |
    v
[SEÇÃO: Escalação de Privilégios]
    |
    v
[SEÇÃO: Lendo as Flags]
    |
    v
[SEÇÃO: Considerações Finais]
   Agradecimento ao autor + reflexão + encorajamento + assinatura
```

---

## PARTE 2 — INVENTÁRIO COMPLETO DE EMOJIS ASCII

| Emoji | Contexto de uso | Frequência |
|-------|----------------|-----------|
| `¯\_(ツ)_/¯` | Ironia, inesperado, "é o que é", "classic CTF" | ★★★★★ |
| `( ͡° ͜ʖ ͡°)` | Algo funciona, suspeita, lenny face | ★★★★★ |
| `(❍ᴥ❍ʋ)` | Assinatura de fechamento OBRIGATÓRIA | ★★★★★ |
| `•̀ᴗ•́` | Descoberta positiva, "encontramos algo" | ★★★★ |
| `ಠᴗಠ` | Satisfação, confiança, orgulho | ★★★★ |
| `(☞ﾟヮﾟ)☞` | Grande sucesso, celebração | ★★★★ |
| `ლ(ಠ_ಠლ)` | Frustração, obstáculo | ★★★★ |
| `( ဖ‿ဖ)人(စ‿စ )` | Abertura entusiasmada, "vamos lá!" | ★★★ |
| `(╯°□°）╯︵ ┻━┻` | Frustração extrema, algo quebrado | ★★★ |
| `( ˘ ³˘)♥` | Bingo!, sucesso suave | ★★★ |
| `ᕕ( ᐛ )ᕗ` | Celebração leve, "conseguimos!" | ★★★ |
| `(⊙_☉)` | Confusão/surpresa | ★★★ |
| `👁 ͜ʖ👁` | Espreitar algo suspeito | ★★★ |
| `(ｏ・_・)ノ"(ᴗ_ ᴗ。)` | "mais uma perda de tempo" | ★★ |
| `ಥ_ಥ` | Tristeza/frustração profunda | ★★ |
| `( •_•)` | Suspeita leve | ★★ |
| `｡◕‿◕｡` | Celebração suave | ★★ |
| `ԅ(≖‿≖ԅ)` | Algo sinistro/escalada iminente | ★★ |
| `(⨪ˬ⨪)` | Confuso/estranho | ★★ |
| `(•̀ᴗ•́)و ̑̑` | Satisfação com exclamação | ★★ |
| `┬┴┬┴┤ ͜ʖ ͡°) ├┬┴┬┴` | Espreitar/perceber | ★★ |
| `:D` | Alegria/rindo | ★★★ |
| `;)` | Wink / algo implícito | ★★★ |
| `:(` | Frustração | ★★ |
| `ಠ_ಠ` | Desapontamento/incredulidade | ★★ |

**Frases recorrentes:**
- "Bingo!!", "Maravilha!!", "Wow guys!!", "Well Done!!", "Thanks guys!!"
- "huahuahua" (riso descontraído)
- "So... Let's go guys!!"
- "OBS.:" (para observações adicionais)
- "Pode ser apenas um 'buraco do coelho'" (quando algo é rabbit hole)
- "Mais uma perda de tempo!!" (quando uma tentativa falha)
- "Perfeito :)" (pequena conquista)
- "Until the next, guys!!!" (fechamento alternativo)

---

## PARTE 3 — TOM E VOZ

**Características fundamentais:**
1. Escreve para "você" diretamente: "você pode usar X ou Y"
2. Admite limitações e falhas: "Confesso que meu conhecimento em X é básico (ainda)"
3. Documenta caminhos que NÃO funcionaram: "tentei X mas não obtive resultado"
4. Explica o PORQUÊ antes do COMO
5. Oferece alternativas sempre: "você pode usar X, Y ou Z"
6. Celebra os erros como aprendizado
7. Faz perguntas retóricas: "Será algum usuário do FTP ou SSH? ¯\_(ツ)_/¯"
8. Referências pessoais: "em uma boa e velha 'Googlada'"
9. Identifica armadilhas explicitamente: "cuidado, este pode ser um rabbit hole"
10. Encoraja o leitor repetidamente ao longo do artigo

**Progressão narrativa em 7 etapas:**
1. Descoberta: "Encontramos X" / "O scanner retornou..."
2. Contexto: "Isso significa que..." / "Observe que..."
3. Hipótese: "Ao que tudo indica..." / "Provavelmente..."
4. Ação: "Vamos então tentar..." / "Desta forma..."
5. Resultado: "Wow!! Bingo!!" / "Infelizmente..."
6. Reflexão: "Perceba que..." / "Aqui podemos ver que..."
7. Alternativas: "Você também pode tentar..."

---

## PARTE 4 — ESTRUTURA DE COMANDOS

```markdown
[Explicação do que vai fazer e POR QUÊ]

```bash
comando -parametro valor
# comentário explicando flag não óbvia
```

[Explicação do output esperado]

[opcional] OBS.: nota importante sobre o comando
[opcional] Alternativas: "você pode usar X, Y ou Z para o mesmo resultado"
```

---

## PARTE 5 — BENCHMARK BEST-OF-THREE (RESULTADO FINAL)

Versão vencedora: **V2 "Structured Narrative"** com elementos do V3

| Critério | V1 Authentic | V2 Structured | V3 Tutorial-First |
|----------|:---:|:---:|:---:|
| Fidelidade ao tom/voz | 10 | 9 | 8 |
| Emojis naturais | 10 | 9 | 7 |
| Detalhe "for dummies" | 7 | 8 | 10 |
| Navegabilidade GitHub | 6 | 10 | 9 |
| Mix técnica + pedagogia | 8 | 9 | 10 |
| Abertura + fechamento | 10 | 9 | 8 |
| Comandos contextualizados | 9 | 8 | 10 |
| Referências e links | 8 | 9 | 10 |
| Reproduzibilidade e2e | 8 | 9 | 10 |
| Diferencial / não-clichê | 9 | 9 | 8 |
| **TOTAL** | **85** | **89** | **90** |

Resultado combinado V2+V3: **91/100**

---

## PARTE 6 — FONTES PREFERIDAS (ORDEM DE PRIORIDADE)

1. Artigo original do André no Medium (máxima autenticidade e autoridade)
2. ExploitDB / SearchSploit (comandos exatos e PoCs)
3. GitHub PoCs do CVE específico
4. Writeups de outros autores reconhecidos (IppSec, 0xdf, S1REN)
5. HackingArticles (ÚLTIMO RECURSO: tem watermark nas imagens)
6. Conhecimento técnico interno (para contexto, alternativas, correlações)

---

## PARTE 7 — REGRAS ABSOLUTAS

1. NUNCA usar travessão "—" como recurso estilístico em texto corrido
   (Substituir por: vírgula, ponto, dois-pontos, ponto-e-vírgula)
2. NUNCA abertura genérica ("In this walkthrough, we will...")
3. SEMPRE terminar com "Thanks guys!! (❍ᴥ❍ʋ)" ou variante
4. SEMPRE seção "Final Thoughts" com agradecimento ao autor da VM
5. NUNCA seção chamada "Introduction" ou "Conclusion"
6. SEMPRE mostrar comandos que NÃO funcionaram (com explicação)
7. SEMPRE oferecer pelo menos uma alternativa de ferramenta/método
8. NUNCA listas secas sem narrativa como corpo principal
9. SEMPRE o PORQUÊ antes do COMO
10. SEMPRE incluir link para artigo original do Medium quando existir
