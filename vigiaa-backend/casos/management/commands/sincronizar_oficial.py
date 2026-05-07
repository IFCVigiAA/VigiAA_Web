from django.core.management.base import BaseCommand
from django.db import connections, transaction

class Command(BaseCommand):
    help = 'Sincroniza TEMP -> OFICIAL (apenas registros novos)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando sincronização entre bancos...")

        try:
            with connections['default'].cursor() as cursor_temp, \
                 transaction.atomic(using='oficial'):

                with connections['oficial'].cursor() as cursor_ofc:

                    # CASOS POSITIVOS
                    cursor_temp.execute("""
                        SELECT hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                               bairro, data_nasc, observacoes, resultado, situacao, geometry,
                               aplicacao, agentes, prim_visita
                        FROM casos_positivos_temp_gl
                    """)
                    dados_pos = cursor_temp.fetchall()

                    if dados_pos:
                        hashes_pos = [d[0] for d in dados_pos]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM casos_positivos WHERE hash_registro = ANY(%s)",
                            [hashes_pos]
                        )
                        existentes_pos = {row[0] for row in cursor_ofc.fetchall()}
                        novos_pos = [d for d in dados_pos if d[0] not in existentes_pos]

                        if novos_pos:
                            cursor_ofc.executemany("""
                                INSERT INTO casos_positivos (
                                    hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                                    bairro, data_nasc, observacoes, resultado, situacao, geometry,
                                    aplicacao, agentes, prim_visita
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, novos_pos)
                        self.stdout.write(f"Positivos — total: {len(dados_pos)} | novos: {len(novos_pos)} | ignorados: {len(existentes_pos)}")

                    # FOCOS
                    cursor_temp.execute("""
                        SELECT hash_registro, n_foco, localidade, imovel, deposito, tipo_atividade, 
                               data_coleta, a_aegypti_form_aquaticas, a_aegypti_form_adultas, 
                               a_albopictus_form_aquaticas, a_albopictus_form_adultas, ovo_a_aegypti, 
                               geometry
                        FROM focos_aedes_temp
                    """)
                    dados_foco = cursor_temp.fetchall()

                    if dados_foco:
                        hashes_foco = [d[0] for d in dados_foco]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM focos_aedes WHERE hash_registro = ANY(%s)",
                            [hashes_foco]
                        )
                        existentes_foco = {row[0] for row in cursor_ofc.fetchall()}
                        novos_foco = [d for d in dados_foco if d[0] not in existentes_foco]

                        if novos_foco:
                            cursor_ofc.executemany("""
                                INSERT INTO focos_aedes (
                                    hash_registro, n_foco, localidade, imovel, deposito, tipo_atividade, 
                                    data_coleta, a_aegypti_form_aquaticas, a_aegypti_form_adultas, 
                                    a_albopictus_form_aquaticas, a_albopictus_form_adultas, ovo_a_aegypti, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, novos_foco)
                        self.stdout.write(f"Focos — total: {len(dados_foco)} | novos: {len(novos_foco)} | ignorados: {len(existentes_foco)}")

                    # PONTOS ESTRATÉGICOS
                    cursor_temp.execute("""
                        SELECT hash_registro, numero, localidade, endereco, complemento, geometry
                        FROM pontos_estrategicos_temp
                    """)
                    dados_ponto = cursor_temp.fetchall()

                    if dados_ponto:
                        hashes_ponto = [d[0] for d in dados_ponto]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM pontos_estrategicos WHERE hash_registro = ANY(%s)",
                            [hashes_ponto]
                        )
                        existentes_ponto = {row[0] for row in cursor_ofc.fetchall()}
                        novos_ponto = [d for d in dados_ponto if d[0] not in existentes_ponto]

                        if novos_ponto:
                            cursor_ofc.executemany("""
                                INSERT INTO pontos_estrategicos (
                                    hash_registro, numero, localidade, endereco, complemento, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                            """, novos_ponto)
                        self.stdout.write(f"Pontos — total: {len(dados_ponto)} | novos: {len(novos_ponto)} | ignorados: {len(existentes_ponto)}")

                    # ARMADILHAS
                    cursor_temp.execute("""
                        SELECT hash_registro, numero, localidade, complemento, tipo_imovel, tipo_armadilha, geometry
                        FROM relat_arm_temp
                    """)
                    dados_arm = cursor_temp.fetchall()

                    if dados_arm:
                        hashes_arm = [d[0] for d in dados_arm]
                        cursor_ofc.execute(
                            "SELECT hash_registro FROM relat_arm WHERE hash_registro = ANY(%s)",
                            [hashes_arm]
                        )
                        existentes_arm = {row[0] for row in cursor_ofc.fetchall()}
                        novos_arm = [d for d in dados_arm if d[0] not in existentes_arm]

                        if novos_arm:
                            cursor_ofc.executemany("""
                                INSERT INTO relat_arm (
                                    hash_registro, numero, localidade, complemento, tipo_imovel, tipo_armadilha, geometry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, novos_arm)
                        self.stdout.write(f"Armadilhas — total: {len(dados_arm)} | novos: {len(novos_arm)} | ignorados: {len(existentes_arm)}")

            self.stdout.write(self.style.SUCCESS("✅ SINCRONIZAÇÃO CONCLUÍDA"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na sincronização: {str(e)}"))
            raise e