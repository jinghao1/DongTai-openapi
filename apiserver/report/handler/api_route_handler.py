######################################################################
# @author      : bidaya0 (bidaya0@$HOSTNAME)
# @file        : api_route_handler
# @created     : Tuesday Aug 17, 2021 19:59:29 CST
#
# @description :
######################################################################

from apiserver.report.handler.report_handler_interface import IReportHandler
from apiserver.report.report_handler_factory import ReportHandler
from dongtai.models.api_route import IastApiRoute, IastApiMethod, \
        IastApiResponse, IastApiParameter, \
        IastApiMethodHttpMethodRelation, HttpMethod
from dongtai.models.agent import IastAgent
from dongtai.utils import const
import logging
from django.utils.translation import gettext_lazy as _
from django.db import transaction
logger = logging.getLogger('dongtai.openapi')


@ReportHandler.register(const.REPORT_API_ROUTE)
class ApiRouteHandler(IReportHandler):
    def parse(self):
        self.api_data = self.detail.get('api_data')
        self.api_routes = map(lambda x: _data_dump(x),self.api_data)

    def save(self):
        try:
            agent = IastAgent.objects.filter(pk=self.agent_id)[0:1]
            if not agent:
                raise ValueError(_("No such agent"))
            agent = agent[0]
            for api_route in self.api_routes:
                http_methods = []
                with transaction.atomic():
                    sid = transaction.savepoint()
                    try:
                        for http_method in api_route['method']:
                            http_method, __ = HttpMethod.objects.get_or_create(
                                method=http_method.upper())
                            http_methods.append(http_method)
                        api_method, is_create = IastApiMethod.objects.get_or_create(
                            method='/'.join(api_route['method']))
                        if is_create:
                            for http_method in http_methods:
                                IastApiMethodHttpMethodRelation.objects.create(
                                    api_method_id=api_method.id,
                                    http_method_id=http_method.id)
                        fields = [
                            'uri', 'code_class', 'description', 'code_file',
                            'controller', 'agent'
                        ]
                        api_route_dict = _dictfilter(api_route, fields)
                        api_route_obj = _route_dump(api_route_dict, api_method,
                                                    agent)
                        api_route_model = IastApiRoute.objects.create(
                            **api_route_obj)
                        parameters = api_route['parameters']
                        for parameter in parameters:
                            parameter_obj = _para_dump(parameter,
                                                       api_route_model)
                            IastApiParameter.objects.create(**parameter_obj)
                        response_obj = _response_dump(
                            {'return_type': api_route['return_type']},
                            api_route_model)
                        IastApiResponse.objects.create(**response_obj)
                    except:
                        transaction.savepoint_rollback(sid)
                logger.info(_('API导航日志记录成功'))
        except Exception as e:
            logger.info(_('API导航日志失败，原因:{}').format(e))


def _data_dump(item):
    item['code_class'] = item['class']
    item['code_file'] = item['file']
    return item


def _route_dump(item, api_method, agent):
    item['method'] = api_method
    item['agent'] = agent
    item['path'] = item['uri']
    del item['uri']
    return item


def _para_dump(item, api_route):
    item['route'] = api_route
    item['parameter_type'] = item['type']
    del item['type']
    return item


def _response_dump(item, api_route):
    item['route'] = api_route
    return item


def _dictfilter(dict_: dict, fields: list):
    return {k: v for k, v in dict_.items() if k in fields}
