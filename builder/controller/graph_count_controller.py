from flask import Blueprint, request, g, current_app, session, Response, jsonify
from utils.Gview import Gview
from utils.common_response_status import CommonResponseStatus
import json
from dao.graph_dao import graph_dao
from dao.graphdb_dao import GraphDB
import requests
import redis
from utils.CommonUtil import commonutil
from utils.ConnectUtil import redisConnect
from service.graph_Service import graph_Service
from common.errorcode import codes
from flasgger import swag_from
import yaml
import os

graph_count_controller_app = Blueprint('graph_count_controller_app', __name__)


def get_entity_egdes_num(graph_id):
    '''Count the number of entities and relationships
    Returns:
        code: return code
        res: If it is correct, it will return as follows
            edges: total number of relationships
            entities: total number of entities
            name2count: Total number of entity and relationship classes
            edge2pros: The number of attributes of the relationship
            entity2pros: The number of attributes of the entity
    '''
    ret_code, obj = graph_Service.getGraphById(graph_id)
    if ret_code != 200:
        return '0'
    res = obj["res"]
    if not bool(obj["res"]):
        return '0'
    graph_baseInfo = res["graph_baseInfo"]
    dbname = ''
    graph_db_id = 0
    for baseInfo in graph_baseInfo:
        dbname = baseInfo["graph_DBName"]
        graph_db_id = baseInfo["graph_db_id"]
    graphdb = GraphDB(graph_db_id)

    try:
        if dbname:
            code, res = graphdb.count(dbname)
            if code != codes.successCode:
                return code, res
            edges, entities, name2count, entity_count, edge_count, edge2pros, entity2pros = res
            return codes.successCode, (edges, entities, name2count, edge2pros, entity2pros)
        else:
            return codes.successCode, (0, 0, {}, {}, {})
    except Exception:
        return codes.successCode, (0, 0, {}, {}, {})


def getGraphCountByid(graph_id):
    edges, entities, edge_pros, entity_pros, properties = 0, 0, 0, 0, 0
    code, res = get_entity_egdes_num(graph_id)
    if code != codes.successCode:
        return code, res
    else:
        edges, entities, name2count, edge2pros, entity2pros = res
        if len(edge2pros.keys()) > 0 and len(name2count.keys()) > 0:
            for k in edge2pros.keys():
                if k in name2count:
                    edge_pros += name2count[k] * edge2pros[k]

        if len(entity2pros.keys()) > 0 and len(name2count.keys()) > 0:
            for k in entity2pros.keys():
                if k in name2count:
                    entity_pros += name2count[k] * entity2pros[k]
        properties = edge_pros + entity_pros
        return codes.successCode, (edges, entities, edge_pros, entity_pros, properties)


def getGraphCount(graph_id):
    edges, entities, edge_pros, entity_pros, properties = 0, 0, 0, 0, 0
    code, res = get_entity_egdes_num(graph_id)
    if code != codes.successCode:
        return code, res
    edges, entities, name2count, edge2pros, entity2pros = res
    properties = edges + entities
    return codes.successCode, (edges, entities, edge_pros, entity_pros, properties)


def get_graph_count_all():
    '''
    Returns the total count of all graph entities, relationships, and attributes
    '''
    entities, edges, properties, all_num = 0, 0, 0, 0
    # select 所有的graph_id对应的graph_baseInfo
    df = graph_dao.getAllGraph()
    df = df.to_dict("records")

    for info in df:
        graph_id = info["id"]
        code, res = getGraphCountByid(graph_id)
        if res == codes.successCode:
            edge_nums, entity_nums, edge_pro, entity_pro, pros = res

            entities += entity_nums
            edges += edge_nums
            properties += pros
        else:
            return code, res

    res = {
        "entities": entities,
        "edges": edges,
        "pro": properties,
        "all": properties
    }

    return codes.successCode, res


GBUILDER_ROOT_PATH = os.getenv('GBUILDER_ROOT_PATH', os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
with open(os.path.join(GBUILDER_ROOT_PATH, 'docs/swagger_definitions.yaml'), 'r') as f:
    swagger_definitions = yaml.load(f, Loader=yaml.FullLoader)
with open(os.path.join(GBUILDER_ROOT_PATH, 'docs/swagger_old_response.yaml'), 'r') as f:
    swagger_old_response = yaml.load(f, Loader=yaml.FullLoader)
    swagger_old_response.update(swagger_definitions)

@graph_count_controller_app.route('/', methods=["GET"])
@swag_from(swagger_definitions)
def graphs_count_all():
    '''
    get the graph count
    get the graph count
    ---
    responses:
        200:
            description: operation success
            schema:
                $ref: '#/definitions/builder/graph_count/graphs_count_all'
    '''
    db = "0"
    r = redisConnect.connect_redis(db, model="read")
    try:
        if r.get("graph_count"):
            res = json.loads(r.get("graph_count"))
            result = {"res": res}

        else:
            result = {"cause": "redis connection error", "status": CommonResponseStatus.SERVER_ERROR.value,
                      "message": "redis connection error", "code": CommonResponseStatus.REQUEST_ERROR.value}
        return result
    except Exception:
        result = {"cause": "redis connection error", "status": CommonResponseStatus.SERVER_ERROR.value,
                  "message": "redis connection error", "code": CommonResponseStatus.REQUEST_ERROR.value}
        return result


@graph_count_controller_app.route('/<graph_id>', methods=["GET"])
@swag_from(swagger_old_response)
def graphs_count_by_id(graph_id):
    '''
    get graph statistics
    get the total number of graph entities, relationships, and attributes by graph id
    ---
    parameters:
        -   name: graph_id
            in: path
            required: true
            description: graph id
            type: integer
    '''
    # graph_id 不是int
    if not graph_id.isdigit():
        return Gview.BuFailVreturn(cause="graph_id must be int ", code=CommonResponseStatus.PARAMETERS_ERROR.value,
                                   message="param error "), CommonResponseStatus.BAD_REQUEST.value
    # graph_id 不存在
    code, ret = graph_Service.checkById(graph_id)
    if code != 0:
        return jsonify(ret), 500
    code, resp = getGraphCount(graph_id)
    if code != codes.successCode:
        edges, entities, properties = "--", "--", "--"
    else:
        edges, entities, edge_pros, entity_pros, properties = resp
    res = {
        "entity_pro": entities,
        "edge_pro": edges,
        "pros": properties
    }
    result = {"res": res}
    return result

