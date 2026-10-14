# SkyDog: 2016 — Catch Me If You Can — Writeup (PT-BR)

> Versão legada. O writeup completo e expandido está em [`../skydog-2016-catch-me-if-you-can/`](../skydog-2016-catch-me-if-you-can/).

| | |
|-|-|
| **IP Alvo** | 192.168.1.100 (DHCP) |
| **Dificuldade** | Médio |
| **Sistema Operacional** | Linux |
| **Flags** | 8 flags (codificadas em hex, CTF multi-etapa) |
| **Fonte** | [VulnHub](https://www.vulnhub.com/entry/skydog-2016-catch-me-if-you-can,172/) |

## Resumo do Ataque

nmap → SSH na porta 22222 → falsificação de User-Agent (IE4) → portal FBI → extração com steghide → SSH como barryallen → forense de memória com Volatility

## Metodologia

1. Descoberta de rede e varredura de portas
2. Enumeração do código-fonte e certificado TLS
3. Falsificação de User-Agent para acessar portal oculto
4. Esteganografia para extrair credenciais SSH
5. Login SSH e coleta de flags
6. Forense de memória com Volatility

---

## Passo 1: Descoberta de Rede

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -sV 192.168.1.100
```

Portas abertas: 80 (HTTP), 443 (HTTPS), 22222 (SSH não padrão).

---

## Passo 2: Enumeração Web

Verifique o certificado TLS e o código-fonte da página para pistas sobre o contexto temático (FBI/Abagnale).

Identifique páginas que exigem um User-Agent específico para acesso.

---

## Passo 3: Falsificação de User-Agent

Algumas páginas restringem o acesso por User-Agent (ex.: Internet Explorer 4):

```bash
curl -A "Mozilla/4.0 (compatible; MSIE 4.0; Windows 98)" http://192.168.1.100/
```

Isso revela o portal FBI com conteúdo adicional e links para imagens.

---

## Passo 4: Esteganografia

Baixe as imagens disponíveis e extraia dados ocultos:

```bash
wget http://192.168.1.100/<imagem>
steghide extract -sf <imagem>
```

A senha (passphrase) pode estar em comentários do código-fonte ou ser vazia. Os dados extraídos contêm credenciais SSH.

---

## Passo 5: Login SSH e Coleta de Flags

```bash
ssh barryallen@192.168.1.100 -p 22222
```

Explore os diretórios do usuário para encontrar flags codificadas em hex. Use `xxd` ou `python3` para decodificá-las:

```bash
echo "<hex_string>" | xxd -r -p
# ou
python3 -c "print(bytes.fromhex('<hex_string>').decode())"
```

---

## Passo 6: Forense de Memória com Volatility

O desafio inclui análise de dump de memória com Volatility:

```bash
volatility -f <memory.dmp> imageinfo
volatility -f <memory.dmp> --profile=<PROFILE> pslist
volatility -f <memory.dmp> --profile=<PROFILE> filescan | grep -i flag
```

As flags codificadas na memória completam o desafio multi-etapa.

---

## Lições Aprendidas

1. **Controle de acesso baseado em User-Agent** não é um mecanismo de segurança real: qualquer cliente pode falsificar o User-Agent.
2. **Dados ocultos via esteganografia** em arquivos de imagem: audite todos os recursos estáticos em engajamentos reais; use `stegdetect` ou `binwalk` para triagem rápida.
3. **SSH em porta não padrão** reduz ruído de bots mas não substitui autenticação por chave: use sempre autenticação por chave pública.
4. **Forense de memória** é uma habilidade essencial para resposta a incidentes: processos, conexões, arquivos abertos e artefatos de malware ficam registrados na RAM mesmo após remoção do disco.

## Remediação

| Vulnerabilidade | Correção |
|---|---|
| Controle de acesso por User-Agent | Implemente autenticação real (tokens, sessões); não confie em User-Agent |
| Dados ocultos em imagens | Processe e recodifique imagens antes de publicar; use CDN com stripping de metadados |
| SSH em porta não padrão sem autenticação por chave | Use autenticação por chave pública; desative login por senha |
| Credenciais em arquivos de imagem | Nunca armazene credenciais em assets estáticos |

Thanks guys!! (❍ᴥ❍ʋ)
